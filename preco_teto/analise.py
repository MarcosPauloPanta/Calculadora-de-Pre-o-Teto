"""Tratamento do histórico anual: tabela ROE/payout/DPA e estatísticas escolhidas.

ROE do ano  = lucro líquido / patrimônio líquido (final do ano).
Payout      = DPA / LPA (limitado a 100% nas estatísticas; o valor bruto fica na tabela).
Anos com PL <= 0 (sem ROE) ou LPA <= 0 (sem payout) são excluídos da respectiva série,
e o motivo aparece na coluna ``obs``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from preco_teto.estatisticas import ESCOLHAS, ResumoEstatistico, resumir
from preco_teto.exceptions import DadosInsuficientesError, ParametroInvalidoError
from preco_teto.models import DadosMercado


@dataclass(frozen=True)
class ParametrosValuation:
    """Escolhas do usuário. ``k`` (retorno exigido) não tem padrão: é decisão dele."""

    k: Optional[float] = None
    janela_anos: int = 10
    min_anos: int = 5
    estat_roe: str = "auto"
    estat_payout: str = "auto"
    estat_dpa: str = "auto"

    def __post_init__(self) -> None:
        if self.k is not None and not (0 < self.k < 1):
            raise ParametroInvalidoError(f"k deve estar entre 0 e 1 (ex.: 0.12 para 12%), recebido {self.k!r}.")
        if not isinstance(self.janela_anos, int) or self.janela_anos < 1:
            raise ParametroInvalidoError("janela_anos deve ser inteiro >= 1.")
        if not isinstance(self.min_anos, int) or not (1 <= self.min_anos <= self.janela_anos):
            raise ParametroInvalidoError("min_anos deve estar entre 1 e janela_anos.")
        for nome in (self.estat_roe, self.estat_payout, self.estat_dpa):
            if nome not in ESCOLHAS:
                raise ParametroInvalidoError(f"Medida '{nome}' inválida; use uma de {ESCOLHAS}.")


@dataclass(frozen=True)
class LinhaAnual:
    ano: int
    lucro_liquido: float
    patrimonio_liquido: float
    lpa: float
    dpa: float
    roe: Optional[float]
    payout: Optional[float]  # bruto
    obs: str = ""


@dataclass(frozen=True)
class AnaliseHistorica:
    ticker: str
    linhas: tuple[LinhaAnual, ...]
    roe: ResumoEstatistico
    payout: ResumoEstatistico
    dpa: ResumoEstatistico
    avisos: tuple[str, ...] = ()

    @property
    def g(self) -> float:
        """Crescimento sustentável: g = ROE x (1 - payout)."""
        return self.roe.valor * (1 - self.payout.valor)

    @property
    def resumos(self) -> tuple[ResumoEstatistico, ...]:
        return (self.roe, self.payout, self.dpa)


class AnalisadorHistorico:
    def analisar(self, dados: DadosMercado, params: ParametrosValuation) -> AnaliseHistorica:
        if not dados.historico:
            raise DadosInsuficientesError(
                f"{dados.ticker}: a fonte de dados não trouxe histórico anual (lucro, patrimônio, LPA, DPA)."
            )
        registros = dados.historico[-params.janela_anos :]
        avisos: list[str] = []
        if len(registros) < params.janela_anos:
            avisos.append(f"histórico com {len(registros)} ano(s), menor que a janela de {params.janela_anos}.")

        linhas: list[LinhaAnual] = []
        roe_serie: list[tuple[int, float]] = []
        payout_serie: list[tuple[int, float]] = []
        dpa_serie: list[tuple[int, float]] = []
        for r in registros:
            obs: list[str] = []
            roe = r.lucro_liquido / r.patrimonio_liquido if r.patrimonio_liquido > 0 else None
            if roe is None:
                obs.append("PL<=0: sem ROE")
            payout = r.dpa / r.lpa if r.lpa > 0 else None
            if payout is None:
                obs.append("LPA<=0: sem payout")
            elif payout > 1:
                obs.append("payout>100% limitado a 100%")
            linhas.append(LinhaAnual(r.ano, r.lucro_liquido, r.patrimonio_liquido, r.lpa, r.dpa, roe, payout, "; ".join(obs)))
            if roe is not None:
                roe_serie.append((r.ano, roe))
            if payout is not None:
                payout_serie.append((r.ano, min(payout, 1.0)))
            dpa_serie.append((r.ano, r.dpa))

        for rotulo, serie in (("ROE", roe_serie), ("payout", payout_serie)):
            if len(serie) < params.min_anos:
                raise DadosInsuficientesError(
                    f"{dados.ticker}: {len(serie)} ano(s) válidos de {rotulo} (mínimo {params.min_anos}). "
                    f"Reduza --min-anos ou use uma fonte com mais histórico."
                )
        return AnaliseHistorica(
            ticker=dados.ticker,
            linhas=tuple(linhas),
            roe=resumir("ROE", roe_serie, params.estat_roe),
            payout=resumir("Payout", payout_serie, params.estat_payout),
            dpa=resumir("DPA", dpa_serie, params.estat_dpa),
            avisos=tuple(avisos),
        )
