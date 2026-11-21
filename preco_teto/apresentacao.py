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
        linhas.append(f"  {m.metodo:<17}: {_brl(m.preco_teto)}   <- {m.detalhe}")
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


def _pct(v):
    return "   -   " if v is None else f"{v:>7.1%}"


def formatar_analise(a) -> str:
    """Tabela anual + estatísticas usadas no cálculo (memória de cálculo)."""
    cab = f"{'Ano':<6}{'Lucro líq.':>16}{'Patrim. líq.':>16}{'LPA':>9}{'DPA':>9}{'ROE':>9}{'Payout':>9}  Obs"
    linhas = [f"Tabela anual - {a.ticker}", cab, "-" * len(cab)]
    for l in a.linhas:
        linhas.append(
            f"{l.ano:<6}{l.lucro_liquido:>16,.0f}{l.patrimonio_liquido:>16,.0f}{l.lpa:>9.2f}{l.dpa:>9.2f}"
            f"{_pct(l.roe):>9}{_pct(l.payout):>9}  {l.obs}"
        )
    linhas += ["", "Estatísticas (valor usado destacado com *)"]
    cab2 = f"{'Variável':<9}{'n':>3}{'Média':>10}{'Mediana':>10}{'Aparada':>10}{'Último':>10}{'CV':>7}  Recomendada / motivo"
    linhas += [cab2, "-" * len(cab2)]
    for r in a.resumos:
        def f(nome, valor):
            txt = f"{valor:.4f}" if r.variavel == "DPA" else f"{valor:.2%}"
            return f"{txt + ('*' if r.escolhida == nome else ''):>10}"
        cv = "-" if r.cv is None else f"{r.cv:.0%}"
        linhas.append(
            f"{r.variavel:<9}{r.n:>3}{f('media', r.media)}{f('mediana', r.mediana)}"
            f"{f('aparada', r.aparada)}{f('ultimo', r.ultimo)}{cv:>7}  {r.recomendada} ({r.motivo})"
        )
    linhas.append(f"\ng = ROE x (1 - payout) = {a.g:.2%}")
    for aviso in a.avisos:
        linhas.append(f"aviso: {aviso}")
    return "\n".join(linhas)
