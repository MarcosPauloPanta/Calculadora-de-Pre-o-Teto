"""Contrato dos métodos de preço teto (ponto de variação do sistema)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from preco_teto.models import DadosMercado, ResultadoMetodo


class MetodoPrecoTeto(ABC):
    """Contrato: transforma :class:`DadosMercado` em um preço teto.

    Entradas
        ``dados``: foto de mercado do ativo; ``hoje``: data de referência
        (injetada para tornar o cálculo determinístico e testável).
    Saída
        :class:`ResultadoMetodo` com ``preco_teto`` > 0 e o detalhamento da conta.
    Falhas previstas
        :class:`~preco_teto.exceptions.DadosInsuficientesError` quando os
        dados não permitem aplicar o método (ex.: lucro negativo, sem proventos).
    """

    @property
    @abstractmethod
    def nome(self) -> str:
        """Nome curto do método, usado nos relatórios."""

    @abstractmethod
    def calcular(self, dados: DadosMercado, hoje: date) -> ResultadoMetodo:
        """Calcula o preço teto ou levanta ``DadosInsuficientesError``."""
