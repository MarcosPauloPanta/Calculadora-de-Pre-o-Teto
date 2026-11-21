# Calculadora de Preço Teto (B3) — v0.2 (base simples)

Trabalho final de Computação II (UFRJ). Integrantes: _(preencher nome e DRE)_.

Dado um ticker, o programa busca os dados, **classifica o ativo** (ação, unit, FII, BDR, ETF) e aplica o método do tipo.
Para ações, o modelo é de **crescimento sustentável** com retorno exigido **k escolhido pelo usuário**:

```
ROE    = lucro líquido / patrimônio líquido (por ano)
payout = DPA / LPA (limitado a 100%)
g      = ROE x (1 - payout)
P/VP justo = (ROE - g) / (k - g)      -> teto = P/VP justo x VPA atual
VF (Gordon) = D x (1 + g) / (k - g)
```

ROE, payout e D vêm de uma janela de **10 anos** (configurável). Para cada variável o programa mostra
média, mediana, média aparada e último valor, **recomenda** uma medida (e explica por quê) e deixa você
**escolher a sua**. O preço teto final é o menor entre os dois métodos.

| Tipo | Método |
|---|---|
| Ação / Unit | P/VP justificado e Gordon (exigem `--k`) |
| FII | DY alvo de 8% sobre os rendimentos de 12 meses |
| BDR / ETF | ainda sem método (mensagem clara) |

> Ferramenta didática. Não é recomendação de investimento.

## Escolhendo a medida (média, mediana...)

Com `auto` (padrão), a recomendação segue uma regra simples e auditável:

* menos de 4 anos: média;
* algum outlier (regra de Tukey **e** afastado da mediana em mais de 20%): mediana;
* coeficiente de variação > 50%: mediana;
* senão: média.

Você sempre pode forçar: `--estat-roe mediana`, `--estat-payout media`, `--estat-dpa aparada` (ou `ultimo`).

## Instalação

Python 3.10+. A dependência só é necessária para dados online (`yfinance`/`auto`):

```bash
pip install -r requirements.txt
```

## Execução

Ver as tabelas e estatísticas **antes** de escolher o k (não exige `--k`):

```bash
python main.py analisar PETR4 TAEE11 --fonte arquivo
```

Calcular com k de 12% ao ano (aceita `0.12`, `12` ou `12%`) e mostrar as tabelas usadas:

```bash
python main.py calcular PETR4 TAEE11 --fonte arquivo --k 12% --tabelas
python main.py calcular PETR4 --fonte arquivo --k 12% --estat-roe media --estat-dpa media   # sua escolha
python main.py calcular PETR4 --fonte arquivo --k 12% --exportar-csv saida/                 # CSV para auditar
python main.py historico
```

Resultado esperado com os dados de exemplo e `--k 12%`: PETR4 teto R$ 49,69 e TAEE11 R$ 15,49 (método Gordon,
conferidos com um cálculo independente); `MGLU3` (prejuízos) e `BOVA11` (ETF) geram erros claros e código de saída 1.

Dados online: `python main.py calcular PETR4 ITUB4 --k 12%` (fonte `auto`: yfinance, depois brapi).

## Testes

```bash
python -m unittest discover -s tests -t . -v
```

## Estrutura

```
main.py
preco_teto/
  ticker.py, classificador.py     ticker -> TipoAtivo
  models.py                       DadosMercado, RegistroAnual (histórico), resultados
  estatisticas.py                 resumo estatístico + recomendação de medida
  analise.py                      ParametrosValuation, tabela anual, AnaliseHistorica
  metodos/                        contrato MetodoPrecoTeto; PVP justificado, Gordon, DY FII
  ativos/                         Ativo (abstrata) + Acao, FundoImobiliario, Bdr, Etf + fábrica
  provedores/                     contrato ProvedorDados; arquivo JSON, yfinance, brapi, fallback
  repositorio.py, exportacao.py   histórico JSON (atômico) e CSV das tabelas
  servico.py, cli.py              orquestração e linha de comando
tests/                            78 testes (unittest)
data/exemplos/                    dados FICTÍCIOS (12 anos) para execução offline
```

## Fontes de dados e limitações (leia)

- **yfinance**: dá preço, VPA e dividendos de longo prazo, mas as demonstrações anuais (lucro, patrimônio, LPA)
  costumam vir com **só ~4-5 anos**. Com menos de `--min-anos` anos válidos o programa avisa e recusa o cálculo.
- **Próxima fonte recomendada para 10+ anos de ROE: CVM dados abertos** (DFP anual desde 2010, grátis, sem chave).
  Falta mapear ticker -> CNPJ e ações em circulação; ficou para a próxima etapa.
- **brapi.dev**: traz preço e dividendos; o histórico anual ainda não foi integrado. Tickers fora de
  PETR4/VALE3/MGLU3/ITUB4 exigem token (`BRAPI_TOKEN`).
- As fontes online não foram executadas ao vivo no ambiente de desenvolvimento (sem internet); foram testadas com
  respostas simuladas. Validar com dados reais.
- Se g >= k o modelo diverge e o programa recusa o cálculo (aumente k ou escolha outra medida).
- Dados de exemplo são fictícios.


## Integração inicial com a CVM (em desenvolvimento)

A coleta oficial foi iniciada em `preco_teto/provedores/cvm.py`. O módulo resolve ticker via FCA e baixa DFP anual, preservando contas contábeis, versão, grupo, período, moeda, escala e arquivo de origem. Os ZIPs ficam em `.cache/cvm` (não devem ser versionados).

Esta primeira etapa **não gera preço teto com dados CVM ainda**: DFP fornece valores da companhia, enquanto LPA/DPA por ação exigem quantidade de ações e proventos consistentes. Também é necessária uma fonte independente para cotação atual. Consulte [docs/CVM_PIPELINE.md](docs/CVM_PIPELINE.md) antes de interpretar os dados.

Fontes oficiais: [FCA](https://dados.cvm.gov.br/dataset/cia_aberta-doc-fca) · [DFP](https://dados.cvm.gov.br/dataset/cia_aberta-doc-dfp).
