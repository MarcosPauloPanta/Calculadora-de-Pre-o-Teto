"""Métodos baseados em proventos: Bazin (ações) e DY alvo (FIIs).

``MetodoPorDividendos`` é a especialização comum; ``MetodoBazin`` e
``MetodoDYFii`` só fixam nome e parâmetros-padrão. Herança usada porque as três
classes são realmente a mesma regra (teto = provento anual / yield alvo).
"""
from __future__ import annotations

from datetime import date

from preco_teto.exceptions import DadosInsuficientesError, ParametroInvalidoError
from preco_teto.metodos.base import MetodoPrecoTeto
from preco_teto.models import DadosMercado, ResultadoMetodo


class MetodoPorDividendos(MetodoPrecoTeto):
    """teto = (proventos anualizados na janela) / yield alvo."""

    def __init__(self, nome: str, yield_alvo: float, janela_meses: int = 12) -> None:
        if not (0 < yield_alvo <= 1):
            raise ParametroInvalidoError(f"yield_alvo deve estar em (0, 1], recebido {yield_alvo!r}.")
        if not isinstance(janela_meses, int) or janela_meses <= 0:
            raise ParametroInvalidoError(f"janela_meses deve ser inteiro > 0, recebido {janela_meses!r}.")
        self._nome = nome
        self._yield_alvo = yield_alvo
        self._janela_meses = janela_meses

    @property
    def nome(self) -> str:
        return self._nome

    @property
    def yield_alvo(self) -> float:
        return self._yield_alvo

    def calcular(self, dados: DadosMercado, hoje: date) -> ResultadoMetodo:
        total = dados.total_proventos(self._janela_meses, hoje)
        if total <= 0:
            raise DadosInsuficientesError(
                f"{dados.ticker}: sem proventos nos últimos {self._janela_meses} meses; "
                f"método {self._nome} não aplicável."
            )
        anual = total * 12 / self._janela_meses
        teto = anual / self._yield_alvo
        detalhe = (
            f"proventos {self._janela_meses}m = {total:.4f} (anualizado {anual:.4f}) "
            f"/ yield alvo {self._yield_alvo:.2%} = {teto:.2f}"
        )
        return ResultadoMetodo(self._nome, teto, detalhe)


class MetodoBazin(MetodoPorDividendos):
    """Método de Décio Bazin: pagar no máximo o preço que rende 6% a.a. em dividendos."""

    def __init__(self, yield_alvo: float = 0.06, janela_meses: int = 12) -> None:
        super().__init__("Bazin", yield_alvo, janela_meses)


class MetodoDYFii(MetodoPorDividendos):
    """Teto por dividend yield alvo para FIIs (padrão: 8% a.a. sobre os rendimentos de 12m)."""

    def __init__(self, yield_alvo: float = 0.08, janela_meses: int = 12) -> None:
        super().__init__("DY alvo (FII)", yield_alvo, janela_meses)
