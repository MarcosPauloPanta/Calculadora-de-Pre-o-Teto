"""Modelos de dados do domínio.

Objetos imutáveis que validam o próprio estado na construção: um dado inválido
nunca chega às regras de cálculo.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional

from preco_teto.datas import subtrair_meses
from preco_teto.exceptions import DadosInvalidosError


def _finito(valor: Any) -> bool:
    return isinstance(valor, (int, float)) and not isinstance(valor, bool) and math.isfinite(valor)


@dataclass(frozen=True)
class Provento:
    """Dividendo/JCP/rendimento pago por cota ou ação."""

    data: date
    valor: float

    def __post_init__(self) -> None:
        if not isinstance(self.data, date):
            raise DadosInvalidosError(f"Data de provento inválida: {self.data!r}")
        if not _finito(self.valor) or self.valor < 0:
            raise DadosInvalidosError(f"Valor de provento inválido: {self.valor!r}")


@dataclass(frozen=True)
class RegistroAnual:
    """Um exercício anual da empresa (valores por ação em R$, totais na mesma unidade)."""

    ano: int
    lucro_liquido: float
    patrimonio_liquido: float
    lpa: float  # lucro por ação
    dpa: float  # dividendos + JCP pagos por ação no ano

    def __post_init__(self) -> None:
        if not isinstance(self.ano, int) or isinstance(self.ano, bool):
            raise DadosInvalidosError(f"Ano inválido: {self.ano!r}")
        for rotulo, v in (("lucro_liquido", self.lucro_liquido), ("patrimonio_liquido", self.patrimonio_liquido),
                          ("lpa", self.lpa), ("dpa", self.dpa)):
            if not _finito(v):
                raise DadosInvalidosError(f"{self.ano}: {rotulo} inválido ({v!r}).")
        if self.dpa < 0:
            raise DadosInvalidosError(f"{self.ano}: dpa não pode ser negativo ({self.dpa!r}).")


@dataclass(frozen=True)
class DadosMercado:
    """Foto dos dados necessários para calcular o preço teto de um ticker."""

    ticker: str
    nome: str
    preco_atual: float
    lpa: Optional[float] = None  # lucro por ação (últimos 12m)
    vpa: Optional[float] = None  # valor patrimonial por ação
    proventos: tuple[Provento, ...] = field(default_factory=tuple)
    historico: tuple[RegistroAnual, ...] = field(default_factory=tuple)  # exercícios anuais

    def __post_init__(self) -> None:
        if not _finito(self.preco_atual) or self.preco_atual <= 0:
            raise DadosInvalidosError(f"{self.ticker}: preço atual inválido ({self.preco_atual!r}).")
        for rotulo, valor in (("LPA", self.lpa), ("VPA", self.vpa)):
            if valor is not None and not _finito(valor):
                raise DadosInvalidosError(f"{self.ticker}: {rotulo} inválido ({valor!r}).")
        anos = [r.ano for r in self.historico]
        if len(anos) != len(set(anos)):
            raise DadosInvalidosError(f"{self.ticker}: histórico anual com anos repetidos.")
        object.__setattr__(
            self, "proventos", tuple(sorted(self.proventos, key=lambda p: p.data))
        )
        object.__setattr__(
            self, "historico", tuple(sorted(self.historico, key=lambda r: r.ano))
        )

    def total_proventos(self, meses: int, hoje: date) -> float:
        """Soma dos proventos pagos em ``(hoje - meses, hoje]``."""
        inicio = subtrair_meses(hoje, meses)
        return sum(p.valor for p in self.proventos if inicio < p.data <= hoje)


@dataclass(frozen=True)
class ResultadoMetodo:
    """Saída de um único método de valuation."""

    metodo: str
    preco_teto: float
    detalhe: str
    # Memória de cálculo (tabelas/estatísticas) para o usuário auditar; não é persistida.
    analise: Any = field(default=None, compare=False, repr=False)

    def to_dict(self) -> dict[str, Any]:
        return {"metodo": self.metodo, "preco_teto": self.preco_teto, "detalhe": self.detalhe}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ResultadoMetodo":
        return cls(d["metodo"], float(d["preco_teto"]), d["detalhe"])


@dataclass(frozen=True)
class ResultadoTeto:
    """Resultado consolidado de um ativo, pronto para exibir e persistir."""

    ticker: str
    nome: str
    tipo: str
    data_referencia: date
    preco_atual: float
    preco_teto: float
    metodo_decisivo: str
    resultados: tuple[ResultadoMetodo, ...]
    avisos: tuple[str, ...] = ()

    @property
    def margem_seguranca(self) -> float:
        """(teto - preço) / teto. Positiva = preço abaixo do teto."""
        return (self.preco_teto - self.preco_atual) / self.preco_teto

    @property
    def veredito(self) -> str:
        return "ABAIXO DO TETO" if self.preco_atual <= self.preco_teto else "ACIMA DO TETO"

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "nome": self.nome,
            "tipo": self.tipo,
            "data_referencia": self.data_referencia.isoformat(),
            "preco_atual": self.preco_atual,
            "preco_teto": self.preco_teto,
            "metodo_decisivo": self.metodo_decisivo,
            "resultados": [r.to_dict() for r in self.resultados],
            "avisos": list(self.avisos),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ResultadoTeto":
        try:
            return cls(
                ticker=d["ticker"],
                nome=d["nome"],
                tipo=d["tipo"],
                data_referencia=date.fromisoformat(d["data_referencia"]),
                preco_atual=float(d["preco_atual"]),
                preco_teto=float(d["preco_teto"]),
                metodo_decisivo=d["metodo_decisivo"],
                resultados=tuple(ResultadoMetodo.from_dict(r) for r in d["resultados"]),
                avisos=tuple(d.get("avisos", [])),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise DadosInvalidosError(f"Registro de resultado malformado: {exc!r}") from exc
