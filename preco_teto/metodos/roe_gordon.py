"""Métodos de crescimento sustentável (g = ROE x (1 - payout)) com k escolhido pelo usuário.

* ``MetodoPVPJustificado``: P/VP justo = (ROE - g) / (k - g); teto = P/VP justo x VPA atual.
* ``MetodoGordon``:         valor futuro/justo VF = D x (1 + g) / (k - g).

Ambos compartilham a obtenção de ROE, payout e g (``_MetodoCrescimentoSustentavel``);
por isso a herança: são duas fórmulas sobre a mesma base de dados tratada.
"""
from __future__ import annotations

from abc import abstractmethod
from datetime import date

from preco_teto.analise import AnaliseHistorica, AnalisadorHistorico, ParametrosValuation
from preco_teto.exceptions import DadosInsuficientesError, ParametroInvalidoError
from preco_teto.metodos.base import MetodoPrecoTeto
from preco_teto.models import DadosMercado, ResultadoMetodo


class _MetodoCrescimentoSustentavel(MetodoPrecoTeto):
    def __init__(self, params: ParametrosValuation) -> None:
        if params.k is None:
            raise ParametroInvalidoError(
                "Informe o retorno exigido k (ex.: --k 0.12 para 12% ao ano): é uma escolha do usuário."
            )
        self._params = params
        self._k: float = params.k

    def calcular(self, dados: DadosMercado, hoje: date) -> ResultadoMetodo:
        analise = AnalisadorHistorico().analisar(dados, self._params)
        roe, payout, g, k = analise.roe.valor, analise.payout.valor, analise.g, self._k
        if roe <= 0:
            raise DadosInsuficientesError(f"{dados.ticker}: ROE {roe:.2%} <= 0; o modelo não se aplica.")
        if payout <= 0:
            raise DadosInsuficientesError(f"{dados.ticker}: payout 0%; sem distribuição o modelo não se aplica.")
        if k <= g:
            raise DadosInsuficientesError(
                f"{dados.ticker}: k ({k:.2%}) <= g ({g:.2%}); o modelo diverge. Aumente k ou use outra medida."
            )
        premissas = (
            f"ROE {roe:.2%} ({analise.roe.escolhida}), payout {payout:.2%} ({analise.payout.escolhida}), "
            f"g=ROE(1-payout)={g:.2%}, k={k:.2%}"
        )
        preco, conta = self._formula(dados, analise, g, k)
        return ResultadoMetodo(self.nome, preco, f"{premissas}; {conta}", analise=analise)

    @abstractmethod
    def _formula(self, dados: DadosMercado, analise: AnaliseHistorica, g: float, k: float) -> tuple[float, str]:
        """Retorna (preço, texto da conta) já com g < k garantido."""


class MetodoPVPJustificado(_MetodoCrescimentoSustentavel):
    @property
    def nome(self) -> str:
        return "P/VP justificado"

    def _formula(self, dados: DadosMercado, analise: AnaliseHistorica, g: float, k: float) -> tuple[float, str]:
        if dados.vpa is None or dados.vpa <= 0:
            raise DadosInsuficientesError(f"{dados.ticker}: VPA atual indisponível ou não positivo.")
        roe = analise.roe.valor
        pvp = (roe - g) / (k - g)
        preco = pvp * dados.vpa
        return preco, f"P/VP justo=(ROE-g)/(k-g)={pvp:.3f} x VPA {dados.vpa:.2f} = {preco:.2f}"


class MetodoGordon(_MetodoCrescimentoSustentavel):
    @property
    def nome(self) -> str:
        return "Gordon"

    def _formula(self, dados: DadosMercado, analise: AnaliseHistorica, g: float, k: float) -> tuple[float, str]:
        d = analise.dpa.valor
        if d <= 0:
            raise DadosInsuficientesError(f"{dados.ticker}: dividendo base D <= 0; Gordon não se aplica.")
        vf = d * (1 + g) / (k - g)
        return vf, f"VF=D(1+g)/(k-g)={d:.4f} x {1 + g:.4f} / {k - g:.4f} = {vf:.2f} (D: {analise.dpa.escolhida})"
