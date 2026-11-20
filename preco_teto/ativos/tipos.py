"""Tipos concretos de ativo e a fábrica que os cria a partir do ``TipoAtivo``."""
from __future__ import annotations

from typing import Optional, Sequence

from preco_teto.ativos.base import Ativo
from preco_teto.classificador import TipoAtivo
from preco_teto.metodos import MetodoBazin, MetodoDYFii, MetodoGraham, MetodoPrecoTeto
from preco_teto.models import DadosMercado
from preco_teto.ticker import Ticker


class Acao(Ativo):
    """Ações (e units): Bazin (renda) e Graham (lucro + patrimônio)."""

    rotulo_tipo = "ACAO"

    @classmethod
    def metodos_padrao(cls) -> list[MetodoPrecoTeto]:
        return [MetodoBazin(), MetodoGraham()]


class FundoImobiliario(Ativo):
    """FIIs: valem os rendimentos distribuídos, não lucro contábil (Graham não se aplica)."""

    rotulo_tipo = "FII"

    @classmethod
    def metodos_padrao(cls) -> list[MetodoPrecoTeto]:
        return [MetodoDYFii()]


class Bdr(Ativo):
    """BDRs: proventos em BRL são pouco representativos; usa-se apenas Graham."""

    rotulo_tipo = "BDR"

    @classmethod
    def metodos_padrao(cls) -> list[MetodoPrecoTeto]:
        return [MetodoGraham()]


class Etf(Ativo):
    """ETFs não têm lucro/dividendo próprio para esses métodos: sem método de teto."""

    rotulo_tipo = "ETF"

    @classmethod
    def metodos_padrao(cls) -> list[MetodoPrecoTeto]:
        return []


class FabricaAtivos:
    """Mapeia ``TipoAtivo`` -> classe de ``Ativo`` (UNIT é tratada como ação)."""

    _REGISTRO: dict[TipoAtivo, type[Ativo]] = {
        TipoAtivo.ACAO: Acao,
        TipoAtivo.UNIT: Acao,
        TipoAtivo.FII: FundoImobiliario,
        TipoAtivo.BDR: Bdr,
        TipoAtivo.ETF: Etf,
    }

    @classmethod
    def criar(
        cls,
        tipo: TipoAtivo,
        ticker: Ticker,
        dados: DadosMercado,
        metodos: Optional[Sequence[MetodoPrecoTeto]] = None,
    ) -> Ativo:
        return cls._REGISTRO[tipo](ticker, dados, metodos)
