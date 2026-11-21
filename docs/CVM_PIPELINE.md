# Pipeline inicial de dados da CVM

## Objetivo

O módulo `preco_teto.provedores.cvm` faz a primeira etapa automática da análise:
resolver ticker -> companhia/CNPJ -> demonstrações contábeis anuais estruturadas.

## Fontes oficiais utilizadas

- **FCA**: `https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/FCA/DADOS/fca_cia_aberta_AAAA.zip`
  - O arquivo `fca_cia_aberta_valor_mobiliario` liga código de negociação a companhia.
  - O arquivo `fca_cia_aberta_geral` fornece dados cadastrais.
- **DFP**: `https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_AAAA.zip`
  - DRE, BPA, BPP e DFC pelo CNPJ/CD_CVM.
  - Os dados da CVM são reapresentáveis; o coletor mantém a versão mais recente por período/grupo/conta.
- Os arquivos são públicos, sem chave, e ficam em `.cache/cvm` por padrão.

A CVM informa que DFP contém balanço, DRE, fluxo de caixa e demais demonstrações, com histórico desde 2010 e atualizações semanais. FCA contém os dados estruturados do formulário cadastral. Consulte os conjuntos oficiais em https://dados.cvm.gov.br/dataset/cia_aberta-doc-dfp e https://dados.cvm.gov.br/dataset/cia_aberta-doc-fca.

## Uso programático

```python
from preco_teto.provedores.cvm import ClienteCVM

cliente = ClienteCVM()
companhia = cliente.buscar_companhia("WEGE3")
print(companhia.cnpj, companhia.nome, companhia.cd_cvm)

relatorio = cliente.obter_relatorio_anual("WEGE3", anos=10)
print(relatorio.anos_disponiveis)
for conta in relatorio.contas:
    print(conta.demonstracao, conta.data_referencia, conta.codigo,
          conta.descricao, conta.valor, conta.moeda)
```

## Limitações explícitas desta etapa

1. FCA e DFP são documentos da **companhia**, não da ação individual. O ticker identifica o emissor; a conversão para valores por ação exige quantidade de ações adequada ao período/classe.
2. DFP não é fonte de cotação atual. O preço de mercado deverá vir de um provedor de cotações separado, com data/hora da consulta.
3. LPA, DPA e proventos ainda não são derivados nesta primeira entrega. Não se deve alimentar os métodos de Gordon/PVP com valores inventados ou misturar lucro consolidado com quantidade de ações incompatível.
4. A seleção entre demonstrações individuais/consolidadas, exercício atual/anterior, moeda e escala deve ser validada antes de produzir indicadores.
5. O coletor preserva descrição, código, grupo, período, versão, escala, moeda e arquivo de origem para permitir auditoria.

## Próximas etapas

- adicionar ITR para atualização trimestral e cálculo de LTM sem somar períodos acumulados incorretamente;
- mapear contas contábeis padronizadas por empresa/setor;
- calcular lucro atribuível aos controladores, PL, dívida líquida, FCO e capex;
- integrar proventos e quantidade de ações, com eventos societários/desdobramentos;
- compor os dados CVM com uma fonte separada de cotação e só então habilitar preço teto automático.


## ITR e trimestre isolado

O método `ClienteCVM.obter_relatorio_trimestral("WEGE3", anos=5)` baixa os arquivos ITR. Para DRE/DFC, os dados podem estar acumulados no exercício. Use `trimestres_isolados(itr.contas, dfp.contas)` para derivar Q1, Q2, Q3 e Q4 sem somar acumulados duplicados.

- Q1 = acumulado 3M.
- Q2 = acumulado 6M - acumulado 3M.
- Q3 = acumulado 9M - acumulado 6M.
- Q4 = DFP anual - acumulado 9M.
- Q4 não é gerado quando a DFP ou o acumulado de 9M está ausente.
- Contas e grupos não são misturados; cada resultado mantém a origem.

**Atenção:** a regra de diferença acumulada é adequada para contas de fluxo (DRE/DFC). Não se deve aplicar essa transformação a contas patrimoniais de estoque (BPA/BPP), que representam posição em uma data. Para balanços, use diretamente a posição de fechamento do trimestre. A integração de indicadores ainda deve selecionar os tipos de conta apropriados.
