"""Comando para baixar e inspecionar demonstrativos oficiais da CVM."""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from preco_teto.exceptions import PrecoTetoError
from preco_teto.provedores.cvm import ClienteCVM


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m preco_teto.cvm_cli",
        description="Baixa DFP/ITR oficiais da CVM e exporta contas contábeis brutas normalizadas.",
    )
    parser.add_argument("ticker", help="ticker B3, por exemplo WEGE3 ou PETR4")
    parser.add_argument("--anos", type=int, default=5, help="janela histórica (padrão: 5)")
    parser.add_argument("--tipo", choices=("dfp", "itr", "ambos"), default="ambos")
    parser.add_argument("--saida", type=Path, default=Path("data/cvm"),
                        help="pasta de saída dos CSVs (padrão: data/cvm)")
    parser.add_argument("--cache", type=Path, default=Path(".cache/cvm"),
                        help="pasta de cache dos ZIPs oficiais")
    return parser


def _exportar(contas, caminho: Path) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    campos = [
        "demonstracao", "data_referencia", "data_inicio_periodo",
        "data_fim_exercicio", "grupo", "ordem_exercicio", "codigo",
        "descricao", "valor_original", "escala_moeda", "valor_convertido",
        "moeda", "versao", "data_recebimento", "arquivo_origem",
    ]
    with caminho.open("w", newline="", encoding="utf-8-sig") as arquivo:
        writer = csv.DictWriter(arquivo, fieldnames=campos, delimiter=";")
        writer.writeheader()
        for conta in contas:
            writer.writerow({
                "demonstracao": conta.demonstracao,
                "data_referencia": conta.data_referencia.isoformat(),
                "data_inicio_periodo": conta.data_inicio_periodo.isoformat()
                    if conta.data_inicio_periodo else "",
                "data_fim_exercicio": conta.data_fim_exercicio.isoformat()
                    if conta.data_fim_exercicio else "",
                "grupo": conta.grupo,
                "ordem_exercicio": conta.ordem_exercicio,
                "codigo": conta.codigo,
                "descricao": conta.descricao,
                "valor_original": conta.valor_original,
                "escala_moeda": conta.escala_moeda,
                "valor_convertido": conta.valor,
                "moeda": conta.moeda,
                "versao": conta.versao,
                "data_recebimento": conta.data_recebimento.isoformat()
                    if conta.data_recebimento else "",
                "arquivo_origem": conta.arquivo_origem,
            })


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        cliente = ClienteCVM(cache_dir=args.cache)
        companhia = cliente.buscar_companhia(args.ticker)
        print(f"Companhia: {companhia.nome}")
        print(f"Ticker: {companhia.ticker} | CNPJ: {companhia.cnpj} | CD_CVM: {companhia.cd_cvm}")
        tipos = ("dfp", "itr") if args.tipo == "ambos" else (args.tipo,)
        for tipo in tipos:
            relatorio = (
                cliente.obter_relatorio_anual(args.ticker, args.anos)
                if tipo == "dfp"
                else cliente.obter_relatorio_trimestral(args.ticker, min(args.anos, 10))
            )
            destino = args.saida / f"{companhia.ticker}_{tipo}.csv"
            _exportar(relatorio.contas, destino)
            print(f"{tipo.upper()}: {len(relatorio.contas)} contas | anos: "
                  f"{', '.join(map(str, relatorio.anos_disponiveis))}")
            print(f"CSV: {destino}")
        return 0
    except PrecoTetoError as exc:
        print(f"ERRO CVM: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
