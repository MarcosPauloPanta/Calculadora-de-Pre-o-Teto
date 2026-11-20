"""Formatação de resultados para o terminal (sem lógica de domínio)."""
from __future__ import annotations

from preco_teto.models import ResultadoTeto


def _brl(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_resultado(r: ResultadoTeto) -> str:
    linhas = [
        f"{r.ticker} - {r.nome} [{r.tipo}]  (referência: {r.data_referencia.isoformat()})",
        f"  Preço atual : {_brl(r.preco_atual)}",
    ]
    for m in r.resultados:
        linhas.append(f"  {m.metodo:<14}: {_brl(m.preco_teto)}   <- {m.detalhe}")
    linhas.append(f"  PREÇO TETO  : {_brl(r.preco_teto)}  (método decisivo: {r.metodo_decisivo})")
    linhas.append(f"  Margem      : {r.margem_seguranca:+.1%}  => {r.veredito}")
    for aviso in r.avisos:
        linhas.append(f"  aviso       : {aviso}")
    return "\n".join(linhas)


def formatar_tabela(resultados: list[ResultadoTeto]) -> str:
    cab = f"{'TICKER':<8}{'TIPO':<6}{'PREÇO':>12}{'TETO':>12}{'MARGEM':>9}  VEREDITO"
    linhas = [cab, "-" * len(cab)]
    for r in resultados:
        linhas.append(
            f"{r.ticker:<8}{r.tipo:<6}{r.preco_atual:>12.2f}{r.preco_teto:>12.2f}"
            f"{r.margem_seguranca:>+9.1%}  {r.veredito}"
        )
    return "\n".join(linhas)
