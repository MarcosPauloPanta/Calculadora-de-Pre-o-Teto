"""Contrato dos provedores de dados de mercado (segundo ponto de variação)."""
from __future__ import annotations

from abc import ABC, abstractmethod

from preco_teto.models import DadosMercado
from preco_teto.ticker import Ticker


class ProvedorDados(ABC):
    """Contrato: obtém a foto de mercado de um ticker.

    Entrada
        ``ticker``: :class:`Ticker` já validado.
    Saída
        :class:`DadosMercado` com preço atual > 0, LPA/VPA (se disponíveis) e
        histórico de proventos.
    Falhas previstas
        * ``TickerNaoEncontradoError``: a fonte não conhece o ticker;
        * ``ProvedorIndisponivelError``: rede, biblioteca, token ou limite;
        * ``DadosInvalidosError``: resposta fora do formato esperado.
    """

    @property
    @abstractmethod
    def nome(self) -> str:
        """Identificação da fonte (para mensagens de erro e README)."""

    @abstractmethod
    def obter(self, ticker: Ticker) -> DadosMercado:
        """Retorna os dados do ticker ou levanta uma falha prevista."""
