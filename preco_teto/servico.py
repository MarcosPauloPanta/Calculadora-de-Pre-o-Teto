"""Serviço de aplicação: orquestra provedor -> classificador -> ativo -> repositório.

Não faz entrada/saída de console; pode ser usado (e testado) sem menus.
"""
from __future__ import annotations

from datetime import date
from typing import Iterable, Optional

from preco_teto.ativos import FabricaAtivos
from preco_teto.classificador import ClassificadorAtivo
from preco_teto.exceptions import PrecoTetoError
from preco_teto.models import ResultadoTeto
from preco_teto.provedores.base import ProvedorDados
from preco_teto.repositorio import RepositorioResultados
from preco_teto.ticker import Ticker


class CalculadoraPrecoTeto:
    def __init__(
        self,
        provedor: ProvedorDados,
        classificador: Optional[ClassificadorAtivo] = None,
        repositorio: Optional[RepositorioResultados] = None,
    ) -> None:
        self._provedor = provedor
        self._classificador = classificador or ClassificadorAtivo()
        self._repositorio = repositorio

    def calcular(self, ticker_texto: str, hoje: Optional[date] = None) -> ResultadoTeto:
        """Calcula e, só se tudo deu certo, persiste o resultado."""
        hoje = hoje or date.today()
        ticker = Ticker(ticker_texto)
        dados = self._provedor.obter(ticker)
        tipo = self._classificador.classificar(ticker, dados)
        ativo = FabricaAtivos.criar(tipo, ticker, dados)
        resultado = ativo.calcular_preco_teto(hoje)
        if self._repositorio is not None:
            self._repositorio.salvar(resultado)
        return resultado

    def calcular_varios(
        self, tickers: Iterable[str], hoje: Optional[date] = None
    ) -> tuple[list[ResultadoTeto], dict[str, PrecoTetoError]]:
        """Processa cada ticker de forma independente; falhas não interrompem o lote."""
        hoje = hoje or date.today()
        ok: list[ResultadoTeto] = []
        erros: dict[str, PrecoTetoError] = {}
        for t in tickers:
            try:
                ok.append(self.calcular(t, hoje))
            except PrecoTetoError as exc:
                erros[str(t)] = exc
        return ok, erros
