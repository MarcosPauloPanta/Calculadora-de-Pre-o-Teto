"""Classificação de um ticker em um tipo de ativo.

Regra principal: o sufixo numérico do ticker na B3.

* 3, 4, 5, 6, 7, 8 -> ações (ON/PN/PNA/PNB...)
* 32, 33, 34, 35, 39 -> BDRs
* 11 -> ambíguo: pode ser FII, ETF ou UNIT. Desempate por listas conhecidas e
  por pistas no nome do ativo (``FII``, ``FUNDO``, ``ETF``...). Sem pistas,
  assume FII, que é o caso mais comum entre os tickers terminados em 11.

A classificação é uma heurística; ver README (limitações).
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from preco_teto.models import DadosMercado
from preco_teto.ticker import Ticker


class TipoAtivo(str, Enum):
    ACAO = "ACAO"
    UNIT = "UNIT"
    FII = "FII"
    BDR = "BDR"
    ETF = "ETF"


_SUFIXOS_ACAO = {3, 4, 5, 6, 7, 8}
_SUFIXOS_BDR = {32, 33, 34, 35, 39}

# Listas pequenas para o protótipo; podem ser movidas para arquivo de configuração.
ETFS_CONHECIDOS = frozenset(
    {"BOVA11", "IVVB11", "SMAL11", "HASH11", "GOLD11", "DIVO11", "FIND11", "MATB11", "XINA11"}
)
UNITS_CONHECIDAS = frozenset(
    {"TAEE11", "KLBN11", "SANB11", "ALUP11", "BPAC11", "SAPR11", "ENGI11", "CPLE11", "BRBI11"}
)
_PISTAS_ETF = ("ETF", "ISHARES", "INDEX", "ÍNDICE", "INDICE")


class ClassificadorAtivo:
    """Decide o :class:`TipoAtivo` de um ticker."""

    def classificar(self, ticker: Ticker, dados: Optional[DadosMercado] = None) -> TipoAtivo:
        sufixo = ticker.sufixo
        if sufixo in _SUFIXOS_ACAO:
            return TipoAtivo.ACAO
        if sufixo in _SUFIXOS_BDR:
            return TipoAtivo.BDR
        if sufixo == 11:
            return self._classificar_sufixo_11(ticker, dados)
        # Sufixos raros (ex.: 12, 13 = direitos/recibos): tratados como ação.
        return TipoAtivo.ACAO

    @staticmethod
    def _classificar_sufixo_11(ticker: Ticker, dados: Optional[DadosMercado]) -> TipoAtivo:
        if ticker.simbolo in ETFS_CONHECIDOS:
            return TipoAtivo.ETF
        if ticker.simbolo in UNITS_CONHECIDAS:
            return TipoAtivo.UNIT
        nome = (dados.nome if dados else "").upper()
        if any(p in nome for p in _PISTAS_ETF):
            return TipoAtivo.ETF
        # Sem pistas de ETF, o padrão para "11" é FII (nomes com FII/FUNDO só confirmam).
        return TipoAtivo.FII
