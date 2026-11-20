"""Objeto de valor ``Ticker``: normaliza e valida códigos da B3."""
from __future__ import annotations

import re
from dataclasses import dataclass

from preco_teto.exceptions import TickerInvalidoError

_PADRAO = re.compile(r"^([A-Z]{4})(\d{1,2})$")


@dataclass(frozen=True)
class Ticker:
    """Código de negociação normalizado (ex.: ``PETR4``).

    Aceita minúsculas, espaços e o sufixo ``.SA`` (convenção do Yahoo).
    """

    simbolo: str

    def __post_init__(self) -> None:
        if not isinstance(self.simbolo, str):
            raise TickerInvalidoError(f"Ticker deve ser texto, recebido: {self.simbolo!r}")
        limpo = self.simbolo.strip().upper()
        if limpo.endswith(".SA"):
            limpo = limpo[:-3]
        if not _PADRAO.match(limpo):
            raise TickerInvalidoError(
                f"Ticker inválido: {self.simbolo!r}. Esperado algo como PETR4, TAEE11 ou AAPL34."
            )
        object.__setattr__(self, "simbolo", limpo)

    @property
    def raiz(self) -> str:
        return self.simbolo[:4]

    @property
    def sufixo(self) -> int:
        """Parte numérica (3, 4, 11, 34...)."""
        return int(self.simbolo[4:])

    def __str__(self) -> str:
        return self.simbolo
