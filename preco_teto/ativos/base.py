"""Classe abstrata ``Ativo``: um ticker + seus dados + os métodos que se aplicam a ele."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Optional, Sequence

from preco_teto.analise import ParametrosValuation
from preco_teto.exceptions import (
    DadosInsuficientesError,
    DadosInvalidosError,
    MetodoNaoAplicavelError,
)
from preco_teto.metodos.base import MetodoPrecoTeto
from preco_teto.models import DadosMercado, ResultadoMetodo, ResultadoTeto
from preco_teto.ticker import Ticker


class Ativo(ABC):
    """Cada subclasse decide *quais* métodos valem para o seu tipo.

    O cálculo em si (template method) é comum: roda cada método do contrato
    :class:`MetodoPrecoTeto`, tolera falhas parciais e consolida pelo menor
    teto (postura conservadora). ``Ativo`` nunca conhece uma classe concreta de método.
    """

    #: rótulo exibido no resultado (ex.: "ACAO", "FII")
    rotulo_tipo: str = "ATIVO"

    def __init__(
        self,
        ticker: Ticker,
        dados: DadosMercado,
        metodos: Optional[Sequence[MetodoPrecoTeto]] = None,
        params: Optional[ParametrosValuation] = None,
    ) -> None:
        if dados.ticker != ticker.simbolo:
            raise DadosInvalidosError(
                f"Dados de {dados.ticker} não pertencem ao ticker {ticker.simbolo}."
            )
        self._ticker = ticker
        self._dados = dados
        self._metodos: tuple[MetodoPrecoTeto, ...] = (
            tuple(metodos) if metodos is not None
            else tuple(self.metodos_padrao(params or ParametrosValuation()))
        )

    @classmethod
    @abstractmethod
    def metodos_padrao(cls, params: ParametrosValuation) -> list[MetodoPrecoTeto]:
        """Métodos de valuation recomendados para este tipo de ativo, já parametrizados."""

    @property
    def ticker(self) -> Ticker:
        return self._ticker

    @property
    def nomes_metodos(self) -> list[str]:
        return [m.nome for m in self._metodos]

    def calcular_preco_teto(self, hoje: date) -> ResultadoTeto:
        if not self._metodos:
            raise MetodoNaoAplicavelError(
                f"{self._ticker}: não há método de preço teto para ativos do tipo {self.rotulo_tipo}."
            )
        sucessos: list[ResultadoMetodo] = []
        avisos: list[str] = []
        for metodo in self._metodos:
            try:
                sucessos.append(metodo.calcular(self._dados, hoje))
            except DadosInsuficientesError as exc:
                avisos.append(f"{metodo.nome}: {exc}")
        if not sucessos:
            raise DadosInsuficientesError(
                f"{self._ticker}: nenhum método aplicável. " + " | ".join(avisos)
            )
        decisivo = min(sucessos, key=lambda r: r.preco_teto)
        return ResultadoTeto(
            ticker=self._ticker.simbolo,
            nome=self._dados.nome,
            tipo=self.rotulo_tipo,
            data_referencia=hoje,
            preco_atual=self._dados.preco_atual,
            preco_teto=decisivo.preco_teto,
            metodo_decisivo=decisivo.metodo,
            resultados=tuple(sucessos),
            avisos=tuple(avisos),
        )
