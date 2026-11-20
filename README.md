# Calculadora de Preço Teto (B3) — protótipo v0.1

Trabalho final de Computação II (UFRJ). Integrantes: _(preencher nome e DRE)_.

Dado um ticker (`PETR4`, `HGLG11`, `AAPL34`...), o programa busca os dados online, **classifica o ativo**
(ação, unit, FII, BDR, ETF) e aplica o(s) método(s) de preço teto adequados ao tipo.

| Tipo | Métodos | Fórmula |
|---|---|---|
| Ação / Unit | Bazin e Graham (vale o **menor** teto) | Bazin: proventos 12m ÷ 6% · Graham: √(22,5 × LPA × VPA) |
| FII | DY alvo | rendimentos 12m ÷ 8% |
| BDR | Graham | √(22,5 × LPA × VPA) |
| ETF | — (recusado com mensagem clara) | — |

> Ferramenta didática. Não é recomendação de investimento.

## Estrutura

```
main.py                      ponto de entrada
preco_teto/
  ticker.py                  Ticker (valida/normaliza)
  classificador.py           ClassificadorAtivo -> TipoAtivo
  models.py                  Provento, DadosMercado, ResultadoMetodo, ResultadoTeto
  metodos/                   contrato MetodoPrecoTeto + Bazin, DY FII, Graham
  ativos/                    Ativo (abstrata) + Acao, FundoImobiliario, Bdr, Etf + FabricaAtivos
  provedores/                contrato ProvedorDados + yfinance, brapi, arquivo JSON, fallback
  repositorio.py             histórico em JSON (gravação atômica)
  servico.py                 CalculadoraPrecoTeto (orquestra tudo, sem I/O de console)
  cli.py / apresentacao.py   linha de comando e formatação
tests/                       52 testes (unittest)
data/exemplos/               dados ILUSTRATIVOS (fictícios) para execução offline
```

## Instalação

Python 3.10+. Só é preciso instalar a dependência se for usar a fonte `yfinance`/`auto`:

```bash
pip install -r requirements.txt     # yfinance==1.8.0 (acesso ao Yahoo Finance, sem chave)
```

Os testes e a fonte `arquivo` usam apenas a biblioteca padrão.

## Execução

Cenário reproduzível offline (dados de exemplo, data de referência fixa):

```bash
python main.py calcular PETR4 TAEE11 HGLG11 AAPL34 BOVA11 MGLU3 --fonte arquivo --data-referencia 2026-11-20
python main.py historico
```

Saída esperada: tetos de R$ 62,50 (PETR4), 23,24 (TAEE11), 165,00 (HGLG11) e 40,67 (AAPL34); `BOVA11`
(ETF) e `MGLU3` (LPA negativo, sem proventos) geram mensagens de erro e o código de saída 1.

Dados reais online:

```bash
python main.py calcular PETR4 ITUB4 HGLG11                 # fonte auto: yfinance, depois brapi
python main.py calcular PETR4 --fonte brapi                # opcional: export BRAPI_TOKEN=...
```

## Testes

```bash
python -m unittest discover -s tests -t . -v
```

## Fontes de dados

- **yfinance** (padrão): preço, `trailingEps` (LPA), `bookValue` (VPA) e histórico de dividendos de `TICKER.SA`.
- **brapi.dev**: API REST; sem token só PETR4, VALE3, MGLU3 e ITUB4. O token é lido de `BRAPI_TOKEN`.
- **arquivo JSON**: `data/exemplos/<TICKER>.json`, usado em testes e demonstrações.

## Limitações conhecidas

- As fontes online (yfinance, brapi) não foram executadas ao vivo no ambiente de desenvolvimento (sem acesso à
  internet); foram testadas com respostas simuladas. Validar com dados reais na máquina do grupo.
- Classificação de tickers terminados em `11` é heurística (listas de ETFs/units + padrão FII).
- Bazin e Graham não se aplicam bem a todos os setores (ex.: bancos, empresas sem lucro).
- Dados de exemplo são fictícios.
