"""Composição de provedores: tenta um após o outro até algum responder."""
from __future__ import annotations

from typing import Sequence

from preco_teto.exceptions import (
    PrecoTetoError,
    ProvedorIndisponivelError,
    TickerNaoEncontradoError,
)
from preco_teto.models import DadosMercado
from preco_teto.provedores.base import ProvedorDados
from preco_teto.ticker import Ticker


class ProvedorComFallback(ProvedorDados):
    """Também é um :class:`ProvedorDados`, então o consumidor não percebe a diferença."""

    def __init__(self, provedores: Sequence[ProvedorDados]) -> None:
        if not provedores:
            raise ValueError("Informe ao menos um provedor.")
        self._provedores = tuple(provedores)

    @property
    def nome(self) -> str:
        return " -> ".join(p.nome for p in self._provedores)

    def obter(self, ticker: Ticker) -> DadosMercado:
        falhas: list[str] = []
        for p in self._provedores:
            try:
                return p.obter(ticker)
            except (ProvedorIndisponivelError, TickerNaoEncontradoError) as exc:
                falhas.append(f"{p.nome}: {exc}")
        raise PrecoTetoError(f"Nenhum provedor atendeu {ticker}. " + " | ".join(falhas))
