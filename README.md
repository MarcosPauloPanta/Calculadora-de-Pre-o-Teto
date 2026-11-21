# Calculadora de Preço Teto (B3)

Trabalho acadêmico de Computação II (UFRJ). Ferramenta didática para estudar coleta de dados financeiros, estatística e métodos de valuation. **Não é recomendação de investimento.**

## Executar pelo IDLE (Python 3.14)

O projeto possui um menu interativo para facilitar a execução em ambiente de aula.

1. Baixe o ZIP do repositório/branch e extraia a pasta inteira, preservando a estrutura de diretórios.
2. Abra o IDLE do Python 3.14.
3. No IDLE, use **File > Open...** e abra o arquivo `main.py` que está na pasta principal do projeto.
4. Pressione **F5** (Run > Run Module).
5. O menu será exibido no Shell do IDLE.

Não abra somente o arquivo `main.py` fora da pasta: os diretórios `preco_teto` e `data` precisam permanecer ao lado dele.

### O que funciona sem instalar bibliotecas adicionais

- Menu do IDLE.
- Exemplo offline com dados fictícios incluídos no projeto.
- Consulta e exportação dos demonstrativos CVM (usa apenas a biblioteca padrão do Python e requer internet).
- Histórico e exportação CSV, conforme as funcionalidades existentes.

### Fontes online de cotação e histórico

A opção de cálculo online usa `yfinance`, que é uma dependência externa. Para instalá-la no mesmo Python 3.14 utilizado pelo IDLE, abra o Prompt de Comando do Windows e execute:

```text
py -3.14 -m pip install -r requirements.txt
```

Se o comando `py -3.14` não existir, use o caminho do interpretador que aparece em **Help > About IDLE** ou execute `python -m pip install -r requirements.txt` no terminal associado à instalação correta.

A instalação de uma biblioteca no Python de outra versão não a disponibiliza automaticamente no Python 3.14.

## Executar pelo terminal (opcional)

O modo de linha de comando foi preservado:

```bash
python main.py analisar PETR4 --fonte arquivo
python main.py calcular PETR4 --fonte arquivo --k 12% --tabelas
python -m preco_teto.cvm_cli WEGE3 --anos 5 --tipo ambos
```

## Métodos e limites atuais

| Tipo | Método implementado no projeto |
|---|---|
| Ação / Unit | P/VP justificado e Gordon (exigem retorno exigido `k`) |
| FII | DY alvo configurado no método |
| BDR / ETF | Sem método de preço teto nesta versão |

O cálculo depende da qualidade, disponibilidade e consistência dos dados da fonte escolhida. A fonte Yahoo Finance pode fornecer histórico anual curto ou incompleto. Os resultados precisam ser conferidos antes de qualquer interpretação.

## Integração com a CVM: etapa de coleta, não valuation completo

O módulo `preco_teto.provedores.cvm` resolve ticker por meio do FCA e baixa demonstrativos DFP e ITR. A opção 3 do menu do IDLE permite exportar os dados para CSV em `data/cvm`; os ZIPs oficiais ficam em `.cache/cvm`.

**Importante:** a coleta CVM ainda não alimenta diretamente os métodos de preço teto. As demonstrações são dados da companhia, e a conversão em indicadores por ação exige seleção contábil, quantidade de ações por período, proventos e eventos societários consistentes. Não interprete os CSVs brutos como preço justo.

Detalhes técnicos: [docs/CVM_PIPELINE.md](docs/CVM_PIPELINE.md).

## Testes

Na raiz do projeto, pelo terminal:

```bash
python -m unittest discover -s tests -t . -v
```

Os testes automatizados são complementares; a coleta ao vivo depende da disponibilidade dos serviços externos.

## Estrutura principal

```text
main.py                       ponto de entrada para IDLE e terminal
preco_teto/                   domínio, métodos, provedores e serviços
  provedores/cvm.py            coleta oficial FCA/DFP/ITR
  cvm_cli.py                   exportação de dados CVM
data/exemplos/                 dados fictícios para demonstração offline
tests/                         testes automatizados
docs/                          documentação técnica
requirements.txt               dependências externas opcionais
```
