"""Utilitários de datas."""
from __future__ import annotations

import calendar
from datetime import date


def subtrair_meses(d: date, meses: int) -> date:
    """Retorna ``d`` menos ``meses`` meses, ajustando o dia ao fim do mês se preciso."""
    total = d.year * 12 + (d.month - 1) - meses
    ano, mes0 = divmod(total, 12)
    mes = mes0 + 1
    dia = min(d.day, calendar.monthrange(ano, mes)[1])
    return date(ano, mes, dia)
