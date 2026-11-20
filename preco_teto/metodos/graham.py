"""Número de Graham: teto = sqrt(22,5 x LPA x VPA)."""
from __future__ import annotations

import math
from datetime import date

from preco_teto.exceptions import DadosInsuficientesError, ParametroInvalidoError
from preco_teto.metodos.base import MetodoPrecoTeto
from preco_teto.models import DadosMercado, ResultadoMetodo


class MetodoGraham(MetodoPrecoTeto):
    """Preço justo de Benjamin Graham (P/L máx. 15 x P/VP máx. 1,5 = 22,5)."""

    def __init__(self, multiplicador: float = 22.5) -> None:
        if not (isinstance(multiplicador, (int, float)) and multiplicador > 0):
            raise ParametroInvalidoError(f"multiplicador deve ser > 0, recebido {multiplicador!r}.")
        self._mult = float(multiplicador)

    @property
    def nome(self) -> str:
        return "Graham"

    def calcular(self, dados: DadosMercado, hoje: date) -> ResultadoMetodo:
        if dados.lpa is None or dados.vpa is None:
            raise DadosInsuficientesError(f"{dados.ticker}: LPA/VPA indisponíveis para Graham.")
        if dados.lpa <= 0 or dados.vpa <= 0:
            raise DadosInsuficientesError(
                f"{dados.ticker}: Graham exige LPA e VPA positivos (LPA={dados.lpa}, VPA={dados.vpa})."
            )
        teto = math.sqrt(self._mult * dados.lpa * dados.vpa)
        detalhe = f"sqrt({self._mult:g} x LPA {dados.lpa:.2f} x VPA {dados.vpa:.2f}) = {teto:.2f}"
        return ResultadoMetodo(self.nome, teto, detalhe)
