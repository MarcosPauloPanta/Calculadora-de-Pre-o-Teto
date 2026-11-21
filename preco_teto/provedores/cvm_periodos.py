"""Conversão de ITR acumulado em valores trimestrais isolados.

A CVM frequentemente informa DRE/DFC acumuladas desde o início do exercício.
Somar diretamente os valores de março, junho e setembro duplica resultados.
Este módulo calcula Q2 = acumulado jun - acumulado mar, Q3 = acumulado set -
acumulado jun e Q4 = DFP anual - acumulado set. Q1 é o acumulado de março.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

from preco_teto.provedores.cvm import ContaContabilCVM


@dataclass(frozen=True)
class ContaTrimestral:
    """Conta de resultado de um trimestre isolado, com sua origem auditável."""

    ano: int
    trimestre: int
    demonstracao: str
    grupo: str
    codigo: str
    descricao: str
    valor: float
    moeda: str
    escala_moeda: str
    metodo_calculo: str
    arquivo_origem: str


def _chave(conta: ContaContabilCVM) -> tuple[str, str, str, str, str]:
    return (
        conta.demonstracao, conta.grupo, conta.codigo,
        conta.moeda, conta.escala_moeda,
    )


def _preferir(a: ContaContabilCVM | None, b: ContaContabilCVM) -> ContaContabilCVM:
    if a is None:
        return b
    # As linhas já vêm deduplicadas pelo coletor; em empate, prioriza recebimento.
    da = a.data_recebimento or date.min
    db = b.data_recebimento or date.min
    return b if db >= da else a


def trimestres_isolados(
    itr: Iterable[ContaContabilCVM],
    dfp: Iterable[ContaContabilCVM] = (),
) -> tuple[ContaTrimestral, ...]:
    """Transforma ITR acumulado em trimestre isolado.

    DFP é necessária para estimar o Q4 (ano completo menos 9M). Sem DFP, Q4
    não é emitido. A função não interpola contas ausentes e não mistura grupos.
    """
    acumulados: dict[tuple[int, int, tuple[str, str, str, str, str]], ContaContabilCVM] = {}
    anuais: dict[tuple[int, tuple[str, str, str, str, str]], ContaContabilCVM] = {}

    for conta in itr:
        mes = conta.data_referencia.month
        if mes not in (3, 6, 9):
            continue
        chave = (conta.data_referencia.year, mes, _chave(conta))
        acumulados[chave] = _preferir(acumulados.get(chave), conta)

    for conta in dfp:
        if conta.data_referencia.month == 12:
            chave = (conta.data_referencia.year, _chave(conta))
            anuais[chave] = _preferir(anuais.get(chave), conta)

    saida: list[ContaTrimestral] = []
    grupos = sorted({(ano, chave) for ano, _, chave in acumulados})
    for ano, chave in grupos:
        anteriores: dict[int, ContaContabilCVM] = {
            mes: c for (a, mes, k), c in acumulados.items()
            if a == ano and k == chave
        }
        for mes, trimestre in ((3, 1), (6, 2), (9, 3)):
            atual = anteriores.get(mes)
            if atual is None:
                continue
            anterior = anteriores.get(mes - 3)
            # ITR valores de DRE/DFC são acumulados; para Q2/Q3 subtrai-se
            # o acumulado imediatamente anterior, não a soma dos trimestres.
            if trimestre == 1:
                valor = atual.valor
                metodo = "ITR acumulado 3M (Q1)"
            elif anterior is not None:
                valor = atual.valor - anterior.valor
                metodo = f"ITR acumulado {mes}M menos {mes-3}M"
            else:
                # Sem o trimestre anterior não há como separar o período.
                continue
            saida.append(ContaTrimestral(
                ano, trimestre, atual.demonstracao, atual.grupo, atual.codigo,
                atual.descricao, valor, atual.moeda, atual.escala_moeda,
                metodo, atual.arquivo_origem,
            ))

        anual = anuais.get((ano, chave))
        nove_meses = anteriores.get(9)
        if anual is not None and nove_meses is not None:
            saida.append(ContaTrimestral(
                ano, 4, anual.demonstracao, anual.grupo, anual.codigo,
                anual.descricao, anual.valor - nove_meses.valor,
                anual.moeda, anual.escala_moeda,
                "DFP anual menos ITR acumulado 9M", anual.arquivo_origem,
            ))

    return tuple(sorted(saida, key=lambda c: (
        c.ano, c.trimestre, c.demonstracao, c.grupo, c.codigo
    )))
