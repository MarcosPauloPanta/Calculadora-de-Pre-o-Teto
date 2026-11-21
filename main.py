"""Ponto de entrada da Calculadora de Preço Teto.

No IDLE: abra este arquivo e pressione F5 para abrir o menu interativo.
No terminal: continue usando os comandos antigos, por exemplo:
    python main.py calcular PETR4 --fonte arquivo --k 12%
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Garante que os imports e os caminhos relativos funcionem mesmo quando o
# arquivo é executado pelo IDLE a partir de outra pasta.
PASTA_PROJETO = Path(__file__).resolve().parent
if str(PASTA_PROJETO) not in sys.path:
    sys.path.insert(0, str(PASTA_PROJETO))
os.chdir(PASTA_PROJETO)


def _ler_texto(pergunta: str, padrao: str = "") -> str:
    complemento = f" [{padrao}]" if padrao else ""
    resposta = input(f"{pergunta}{complemento}: ").strip()
    return resposta or padrao


def _menu_idle() -> int:
    """Interface textual simples, compatível com o IDLE e sem dependências extras."""
    from preco_teto.cli import main as cli_main
    from preco_teto.cvm_cli import main as cvm_main

    while True:
        print("\n" + "=" * 62)
        print("          CALCULADORA DE PREÇO TETO — MENU IDLE")
        print("=" * 62)
        print("1 - Analisar histórico de um ativo (sem calcular preço teto)")
        print("2 - Calcular preço teto (fontes online disponíveis)")
        print("3 - Baixar demonstrativos oficiais da CVM (DFP/ITR)")
        print("4 - Executar exemplo offline (dados fictícios do projeto)")
        print("5 - Consultar histórico de cálculos")
        print("0 - Sair")
        print("-" * 62)

        opcao = input("Escolha uma opção: ").strip()

        if opcao == "0":
            print("Programa encerrado.")
            return 0

        if opcao == "1":
            ticker = _ler_texto("Ticker B3 (ex.: PETR4)").upper()
            if ticker:
                cli_main(["analisar", ticker, "--fonte", "auto"])
            continue

        if opcao == "2":
            ticker = _ler_texto("Ticker B3 (ex.: PETR4)").upper()
            if not ticker:
                print("Ticker não informado.")
                continue
            taxa = _ler_texto("Retorno exigido ao ano (ex.: 12%)", "12%")
            cli_main(["calcular", ticker, "--fonte", "auto", "--k", taxa, "--tabelas"])
            continue

        if opcao == "3":
            ticker = _ler_texto("Ticker B3 (ex.: WEGE3)").upper()
            if not ticker:
                print("Ticker não informado.")
                continue
            anos = _ler_texto("Quantidade de anos", "5")
            tipo = _ler_texto("Tipo: dfp, itr ou ambos", "ambos").lower()
            if tipo not in ("dfp", "itr", "ambos"):
                print("Tipo inválido. Escolha dfp, itr ou ambos.")
                continue
            try:
                cvm_main([ticker, "--anos", anos, "--tipo", tipo])
            except SystemExit as exc:
                # argparse pode encerrar em caso de parâmetro inválido.
                print(f"Consulta encerrada (código {exc.code}).")
            continue

        if opcao == "4":
            ticker = _ler_texto("Ticker de exemplo (PETR4 ou TAEE11)", "PETR4").upper()
            taxa = _ler_texto("Retorno exigido ao ano (ex.: 12%)", "12%")
            cli_main([
                "calcular", ticker, "--fonte", "arquivo",
                "--pasta-dados", "data/exemplos", "--k", taxa, "--tabelas"
            ])
            continue

        if opcao == "5":
            cli_main(["historico"])
            continue

        print("Opção inválida. Digite um número de 0 a 5.")


def main() -> int:
    # Quando executado com F5 no IDLE, normalmente só existe o nome do arquivo
    # em sys.argv. Com argumentos, mantém a interface de linha de comando.
    if len(sys.argv) <= 1:
        try:
            return _menu_idle()
        except KeyboardInterrupt:
            print("\nExecução interrompida pelo usuário.")
            return 130

    from preco_teto.cli import main as cli_main
    return cli_main()


if __name__ == "__main__":
    raise SystemExit(main())
