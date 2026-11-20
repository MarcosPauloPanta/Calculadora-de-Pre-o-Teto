"""Provedor online baseado na API REST da brapi.dev (apenas biblioteca padrão).

Sem token funcionam somente PETR4, VALE3, MGLU3 e ITUB4; os demais tickers exigem
token (variável de ambiente ``BRAPI_TOKEN`` ou parâmetro). O token nunca é gravado no projeto.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import date
from typing import Any, Callable, Optional

from preco_teto.exceptions import (
    DadosInvalidosError,
    ProvedorIndisponivelError,
    TickerNaoEncontradoError,
)
from preco_teto.models import DadosMercado, Provento
from preco_teto.provedores.base import ProvedorDados
from preco_teto.ticker import Ticker

_URL = (
    "https://brapi.dev/api/quote/{ticker}"
    "?fundamental=true&dividends=true&modules=defaultKeyStatistics"
)


class ProvedorBrapi(ProvedorDados):
    def __init__(
        self,
        token: Optional[str] = None,
        timeout: float = 10.0,
        abrir_url: Callable[..., Any] = urllib.request.urlopen,
    ) -> None:
        self._token = token
        self._timeout = timeout
        self._abrir = abrir_url  # injetável para testes sem rede

    @property
    def nome(self) -> str:
        return "brapi.dev"

    def obter(self, ticker: Ticker) -> DadosMercado:
        req = urllib.request.Request(_URL.format(ticker=ticker.simbolo))
        if self._token:
            req.add_header("Authorization", f"Bearer {self._token}")
        try:
            with self._abrir(req, timeout=self._timeout) as resp:
                payload = json.load(resp)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise TickerNaoEncontradoError(f"brapi não conhece {ticker}.") from exc
            if exc.code in (401, 402, 403, 429):
                raise ProvedorIndisponivelError(
                    f"brapi recusou a consulta (HTTP {exc.code}); verifique o token/limite do plano."
                ) from exc
            raise ProvedorIndisponivelError(f"brapi respondeu HTTP {exc.code}.") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise ProvedorIndisponivelError(f"Sem conexão com a brapi: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise DadosInvalidosError(f"brapi devolveu JSON inválido: {exc}") from exc
        return self._converter(ticker, payload)

    @staticmethod
    def _converter(ticker: Ticker, payload: Any) -> DadosMercado:
        try:
            resultados = payload.get("results")
            if not resultados:
                raise TickerNaoEncontradoError(f"brapi sem resultados para {ticker}.")
            r = resultados[0]
            stats = r.get("defaultKeyStatistics") or {}
            cash = (r.get("dividendsData") or {}).get("cashDividends") or []
            proventos = tuple(
                Provento(date.fromisoformat(str(c["paymentDate"])[:10]), float(c["rate"]))
                for c in cash
                if c.get("paymentDate") and c.get("rate") is not None  # ignora declarados e não pagos
            )
            return DadosMercado(
                ticker=ticker.simbolo,
                nome=r.get("longName") or r.get("shortName") or ticker.simbolo,
                preco_atual=float(r["regularMarketPrice"]),
                lpa=r.get("earningsPerShare"),
                vpa=stats.get("bookValue"),
                proventos=proventos,
            )
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise DadosInvalidosError(f"Resposta inesperada da brapi para {ticker}: {exc!r}") from exc
