"""Interface de linha de comando. Só traduz argumentos/saídas; a lógica está no serviço."""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path
from typing import Optional, Sequence

from preco_teto.analise import ParametrosValuation
from preco_teto.apresentacao import formatar_analise, formatar_resultado, formatar_tabela
from preco_teto.estatisticas import ESCOLHAS
from preco_teto.exceptions import PrecoTetoError
from preco_teto.exportacao import exportar_csv
from preco_teto.provedores import (
    ProvedorArquivoJson,
    ProvedorBrapi,
    ProvedorComFallback,
    ProvedorDados,
    ProvedorYFinance,
)
from preco_teto.repositorio import RepositorioResultados
from preco_teto.servico import CalculadoraPrecoTeto

HISTORICO_PADRAO = Path("data/historico.json")


def _taxa(texto: str) -> float:
    """Aceita 0.12, 12 ou 12% (valores > 1 são tratados como percentual)."""
    try:
        v = float(texto.strip().rstrip("%").replace(",", "."))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"taxa inválida: {texto!r} (ex.: 0.12 ou 12%)") from exc
    return v / 100 if v > 1 else v


def _criar_provedor(fonte: str, pasta_dados: Path) -> ProvedorDados:
    if fonte == "arquivo":
        return ProvedorArquivoJson(pasta_dados)
    if fonte == "yfinance":
        return ProvedorYFinance()
    brapi = ProvedorBrapi(token=os.environ.get("BRAPI_TOKEN"))
    if fonte == "brapi":
        return brapi
    return ProvedorComFallback([ProvedorYFinance(), brapi])  # "auto"


def _opcoes_comuns(p: argparse.ArgumentParser) -> None:
    p.add_argument("tickers", nargs="+", help="ex.: PETR4 TAEE11 HGLG11")
    p.add_argument("--fonte", choices=["auto", "yfinance", "brapi", "arquivo"], default="auto")
    p.add_argument("--pasta-dados", type=Path, default=Path("data/exemplos"),
                   help="pasta com <TICKER>.json (fonte 'arquivo')")
    p.add_argument("--k", type=_taxa, default=None,
                   help="retorno exigido a.a. (ex.: 0.12 ou 12%%); obrigatório para ações")
    p.add_argument("--janela-anos", type=int, default=10, help="anos de histórico usados (padrão 10)")
    p.add_argument("--min-anos", type=int, default=5, help="mínimo de anos válidos (padrão 5)")
    for nome in ("roe", "payout", "dpa"):
        p.add_argument(f"--estat-{nome}", choices=ESCOLHAS, default="auto",
                       help=f"medida central para {nome.upper()} (padrão: auto = recomendada)")
    p.add_argument("--exportar-csv", type=Path, default=None, metavar="PASTA",
                   help="grava as tabelas de cálculo em CSV nesta pasta")


def _montar_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="main.py", description="Calculadora de preço teto (B3).")
    sub = p.add_subparsers(dest="comando", required=True)

    c = sub.add_parser("calcular", help="calcula o preço teto (ROE/payout/Gordon para ações)")
    _opcoes_comuns(c)
    c.add_argument("--data-referencia", type=date.fromisoformat, default=None, help="AAAA-MM-DD (padrão: hoje)")
    c.add_argument("--historico", type=Path, default=HISTORICO_PADRAO)
    c.add_argument("--sem-salvar", action="store_true", help="não grava no histórico")
    c.add_argument("--tabelas", action="store_true", help="mostra as tabelas usadas no cálculo")

    a = sub.add_parser("analisar", help="só mostra tabela anual e estatísticas (não exige --k)")
    _opcoes_comuns(a)

    h = sub.add_parser("historico", help="lista resultados já calculados")
    h.add_argument("--historico", type=Path, default=HISTORICO_PADRAO)
    return p


def _params(args: argparse.Namespace) -> ParametrosValuation:
    return ParametrosValuation(
        k=args.k, janela_anos=args.janela_anos, min_anos=args.min_anos,
        estat_roe=args.estat_roe, estat_payout=args.estat_payout, estat_dpa=args.estat_dpa,
    )


def _exportar(analise, pasta: Optional[Path]) -> None:
    if pasta is not None:
        for caminho in exportar_csv(analise, pasta):
            print(f"CSV gravado: {caminho}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _montar_parser().parse_args(argv)

    if args.comando == "historico":
        try:
            registros = RepositorioResultados(args.historico).listar()
        except PrecoTetoError as exc:
            print(f"ERRO: {exc}", file=sys.stderr)
            return 2
        print(formatar_tabela(registros) if registros else "Histórico vazio.")
        return 0

    try:
        params = _params(args)
    except PrecoTetoError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    repo = None if args.comando == "analisar" or args.sem_salvar else RepositorioResultados(args.historico)
    calc = CalculadoraPrecoTeto(_criar_provedor(args.fonte, args.pasta_dados), repositorio=repo)

    if args.comando == "analisar":
        falhou = False
        for t in args.tickers:
            try:
                analise = calc.analisar(t, params)
                print(formatar_analise(analise), end="\n\n")
                _exportar(analise, args.exportar_csv)
            except PrecoTetoError as exc:
                falhou = True
                print(f"ERRO [{t}]: {exc}", file=sys.stderr)
        return 1 if falhou else 0

    ok, erros = calc.calcular_varios(args.tickers, args.data_referencia, params)
    for r in ok:
        print(formatar_resultado(r))
        analise = next((m.analise for m in r.resultados if m.analise is not None), None)
        if analise is not None:
            if args.tabelas:
                print()
                print(formatar_analise(analise))
            _exportar(analise, args.exportar_csv)
        print()
    if ok:
        print(formatar_tabela(ok))
        if repo is not None:
            print(f"\nResultados salvos em {args.historico}")
    for ticker, exc in erros.items():
        print(f"ERRO [{ticker}]: {exc}", file=sys.stderr)
    return 0 if not erros else 1
