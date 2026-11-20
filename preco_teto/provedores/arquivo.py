"""Provedor offline: lê ``<pasta>/<TICKER>.json``. Usado em testes e demonstrações."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from preco_teto.exceptions import DadosInvalidosError, TickerNaoEncontradoError
from preco_teto.models import DadosMercado, Provento
from preco_teto.provedores.base import ProvedorDados
from preco_teto.ticker import Ticker


class ProvedorArquivoJson(ProvedorDados):
    def __init__(self, pasta: Path | str) -> None:
        self._pasta = Path(pasta)

    @property
    def nome(self) -> str:
        return f"arquivo JSON ({self._pasta})"

    def obter(self, ticker: Ticker) -> DadosMercado:
        caminho = self._pasta / f"{ticker.simbolo}.json"
        try:
            with caminho.open("r", encoding="utf-8") as f:
                bruto = json.load(f)
        except FileNotFoundError as exc:
            raise TickerNaoEncontradoError(
                f"Sem arquivo de dados para {ticker} em {self._pasta}."
            ) from exc
        except json.JSONDecodeError as exc:
            raise DadosInvalidosError(f"Arquivo {caminho.name} não é JSON válido: {exc}") from exc
        return self._converter(ticker, bruto, caminho.name)

    @staticmethod
    def _converter(ticker: Ticker, bruto: Any, origem: str) -> DadosMercado:
        try:
            proventos = tuple(
                Provento(date.fromisoformat(p["data"]), float(p["valor"]))
                for p in bruto.get("proventos", [])
            )
            return DadosMercado(
                ticker=ticker.simbolo,
                nome=bruto["nome"],
                preco_atual=float(bruto["preco_atual"]),
                lpa=bruto.get("lpa"),
                vpa=bruto.get("vpa"),
                proventos=proventos,
            )
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise DadosInvalidosError(f"{origem}: formato inesperado ({exc!r}).") from exc
