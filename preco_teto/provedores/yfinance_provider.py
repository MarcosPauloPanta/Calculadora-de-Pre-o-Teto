"""Provedor online baseado na biblioteca ``yfinance`` (Yahoo Finance; sem chave de API).

Tickers da B3 usam o sufixo ``.SA``. Campos usados: ``currentPrice``, ``bookValue`` (VPA),
``longName``, a série ``dividends`` e, para o histórico anual, ``income_stmt`` (Net Income,
EPS) e ``balance_sheet`` (Stockholders Equity).

LIMITAÇÃO: o Yahoo costuma entregar só ~4-5 exercícios anuais nas demonstrações (os dividendos
vêm de bem mais longe). Para 10+ anos de ROE, a próxima fonte a construir é a CVM (dados abertos).
"""
from __future__ import annotations

import math
from typing import Any, Callable, Optional

from preco_teto.exceptions import (
    DadosInvalidosError,
    ProvedorIndisponivelError,
    TickerNaoEncontradoError,
)
from preco_teto.models import DadosMercado, Provento, RegistroAnual
from preco_teto.provedores.base import ProvedorDados
from preco_teto.ticker import Ticker


def _cliente_padrao(simbolo_yahoo: str) -> Any:
    try:
        import yfinance  # importação tardia: dependência só é exigida ao usar este provedor
    except ImportError as exc:
        raise ProvedorIndisponivelError(
            "Biblioteca 'yfinance' não instalada (pip install -r requirements.txt)."
        ) from exc
    return yfinance.Ticker(simbolo_yahoo)


class ProvedorYFinance(ProvedorDados):
    def __init__(self, fabrica_cliente: Optional[Callable[[str], Any]] = None) -> None:
        # ``fabrica_cliente`` permite injetar um objeto simulado nos testes.
        self._fabrica = fabrica_cliente or _cliente_padrao

    @property
    def nome(self) -> str:
        return "Yahoo Finance (yfinance)"

    def obter(self, ticker: Ticker) -> DadosMercado:
        cliente = self._fabrica(f"{ticker.simbolo}.SA")
        try:
            info = cliente.info or {}
            serie = cliente.dividends
            lucro = _serie_anual(cliente.income_stmt, ('Net Income Common Stockholders', 'Net Income'))
            lpa = _serie_anual(cliente.income_stmt, ('Diluted EPS', 'Basic EPS'))
            pl = _serie_anual(cliente.balance_sheet, ('Stockholders Equity', 'Common Stock Equity'))
        except _erros_yfinance() as exc:
            raise ProvedorIndisponivelError(f"Falha ao consultar o Yahoo Finance: {exc}") from exc

        preco = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
        if not preco:
            raise TickerNaoEncontradoError(f"Yahoo Finance não retornou preço para {ticker}.")
        try:
            proventos = tuple(
                Provento(ts.date(), float(valor)) for ts, valor in serie.items()
            )
            dpa_ano: dict[int, float] = {}
            for p in proventos:
                dpa_ano[p.data.year] = dpa_ano.get(p.data.year, 0.0) + p.valor
            historico = tuple(
                RegistroAnual(ano, lucro[ano], pl[ano], lpa[ano], dpa_ano.get(ano, 0.0))
                for ano in sorted(set(lucro) & set(pl) & set(lpa))
            )
            return DadosMercado(
                ticker=ticker.simbolo,
                nome=info.get("longName") or info.get("shortName") or ticker.simbolo,
                preco_atual=float(preco),
                lpa=info.get("trailingEps"),
                vpa=info.get("bookValue"),
                proventos=proventos,
                historico=historico,
            )
        except (AttributeError, TypeError, ValueError) as exc:
            raise DadosInvalidosError(f"Resposta inesperada do Yahoo para {ticker}: {exc!r}") from exc


def _serie_anual(tabela: Any, nomes: tuple[str, ...]) -> dict[int, float]:
    """Extrai {ano: valor} da primeira linha existente em ``nomes`` (ignora NaN)."""
    if tabela is None:
        return {}
    for nome in nomes:
        if nome in tabela.index:
            return {
                ts.year: float(v)
                for ts, v in tabela.loc[nome].items()
                if v is not None and math.isfinite(float(v))
            }
    return {}


def _erros_yfinance() -> tuple[type[BaseException], ...]:
    """Exceções esperadas da yfinance/rede (sem capturar ``Exception`` genérica)."""
    try:
        from yfinance.exceptions import YFException
    except ImportError:
        return (OSError,)
    return (YFException, OSError)
