"""Tipos concretos de ativo e a fábrica que os cria a partir do ``TipoAtivo``."""
from __future__ import annotations

from typing import Optional, Sequence

from preco_teto.analise import ParametrosValuation
from preco_teto.ativos.base import Ativo
from preco_teto.classificador import TipoAtivo
from preco_teto.metodos import MetodoDYFii, MetodoGordon, MetodoPrecoTeto, MetodoPVPJustificado
from preco_teto.models import DadosMercado
from preco_teto.ticker import Ticker


class Acao(Ativo):
    """Ações (e units): P/VP justificado e Gordon, ambos com g = ROE(1-payout) e k do usuário."""

    rotulo_tipo = "ACAO"

    @classmethod
    def metodos_padrao(cls, params: ParametrosValuation) -> list[MetodoPrecoTeto]:
        return [MetodoPVPJustificado(params), MetodoGordon(params)]


class FundoImobiliario(Ativo):
    """FIIs: valem os rendimentos distribuídos (lucro contábil/ROE não se aplicam)."""

    rotulo_tipo = "FII"

    @classmethod
    def metodos_padrao(cls, params: ParametrosValuation) -> list[MetodoPrecoTeto]:
        return [MetodoDYFii()]


class Bdr(Ativo):
    """BDRs: ainda sem método (sem histórico da empresa no exterior nesta base)."""

    rotulo_tipo = "BDR"

    @classmethod
    def metodos_padrao(cls, params: ParametrosValuation) -> list[MetodoPrecoTeto]:
        return []


class Etf(Ativo):
    """ETFs não têm lucro/dividendo próprio para esses métodos."""

    rotulo_tipo = "ETF"

    @classmethod
    def metodos_padrao(cls, params: ParametrosValuation) -> list[MetodoPrecoTeto]:
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
        params: Optional[ParametrosValuation] = None,
    ) -> Ativo:
        return cls._REGISTRO[tipo](ticker, dados, metodos, params)
