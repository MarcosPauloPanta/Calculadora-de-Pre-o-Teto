"""Interface de linha de comando. Só traduz argumentos/saídas; a lógica está no serviço."""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path
from typing import Optional, Sequence

from preco_teto.apresentacao import formatar_resultado, formatar_tabela
from preco_teto.exceptions import PrecoTetoError
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


def _criar_provedor(fonte: str, pasta_dados: Path) -> ProvedorDados:
    if fonte == "arquivo":
        return ProvedorArquivoJson(pasta_dados)
    if fonte == "yfinance":
        return ProvedorYFinance()
    brapi = ProvedorBrapi(token=os.environ.get("BRAPI_TOKEN"))
    if fonte == "brapi":
        return brapi
    return ProvedorComFallback([ProvedorYFinance(), brapi])  # "auto"


def _montar_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="main.py", description="Calculadora de preço teto (B3).")
    sub = p.add_subparsers(dest="comando", required=True)

    c = sub.add_parser("calcular", help="calcula o preço teto de um ou mais tickers")
    c.add_argument("tickers", nargs="+", help="ex.: PETR4 HGLG11 AAPL34")
    c.add_argument("--fonte", choices=["auto", "yfinance", "brapi", "arquivo"], default="auto")
    c.add_argument("--pasta-dados", type=Path, default=Path("data/exemplos"),
                   help="pasta com <TICKER>.json (fonte 'arquivo')")
    c.add_argument("--data-referencia", type=date.fromisoformat, default=None,
                   help="AAAA-MM-DD (padrão: hoje)")
    c.add_argument("--historico", type=Path, default=HISTORICO_PADRAO)
    c.add_argument("--sem-salvar", action="store_true", help="não grava no histórico")

    h = sub.add_parser("historico", help="lista resultados já calculados")
    h.add_argument("--historico", type=Path, default=HISTORICO_PADRAO)
    return p


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

    repo = None if args.sem_salvar else RepositorioResultados(args.historico)
    calc = CalculadoraPrecoTeto(_criar_provedor(args.fonte, args.pasta_dados), repositorio=repo)
    ok, erros = calc.calcular_varios(args.tickers, args.data_referencia)

    for r in ok:
        print(formatar_resultado(r))
        print()
    if ok:
        print(formatar_tabela(ok))
        if repo is not None:
            print(f"\nResultados salvos em {args.historico}")
    for ticker, exc in erros.items():
        print(f"ERRO [{ticker}]: {exc}", file=sys.stderr)
    return 0 if not erros else 1
