# 1. Inventário e classificação de dados

## 1.1 Premissa

O dataset (Home Credit Default Risk, Kaggle) é público e foi anonimizado pela fonte. Para que a governança seja avaliável, o projeto o trata **como se fosse dado real** de clientes de uma fintech brasileira, sujeito à LGPD (Lei 13.709/2018). Todas as decisões abaixo seguem essa premissa.

## 1.2 Minimização na origem (art. 6º, III — necessidade)

| Etapa | Colunas | Evidência |
|---|---|---|
| Arquivo de origem (`application_train.csv`) | 122 | — |
| Ingestão (`data/ingest.py`, `usecols`) | **21** | `config.py`: `ID_COL`, `TARGET`, `SENSITIVE_COLS`, `FEATURES` |
| Modelo (`MODEL_FEATURES`) | 21 features (15 numéricas, incluindo 4 derivadas, + 6 categóricas) | `data/features.py` |

As 101 colunas não selecionadas **nunca entram no pipeline**: não são lidas, armazenadas nem processadas. Critério de seleção: relevância preditiva documentada em crédito, interpretabilidade e viabilidade de regra de contrato e de monitoramento de drift.

## 1.3 Classificação por coluna

**Legenda de tratamento:** M = usado no modelo · A = mantido só para auditoria · C = chave técnica · R = rótulo

| Coluna | Categoria (LGPD) | Natureza | Tratamento | Justificativa |
|---|---|---|---|---|
| `SK_ID_CURR` | Identificador pseudonimizado | Chave substituta (não é CPF) | C | Rastreabilidade, unicidade de lote, junção com rótulos atrasados e atendimento a direitos do titular (art. 18). Nunca é feature. Em produção, o CPF seria pseudonimizado na origem |
| `TARGET` | Dado pessoal: histórico de adimplemento | Informação de crédito | R | Necessário para treino e monitoramento de performance. Sujeito aos prazos do CDC, art. 43, e da Lei do Cadastro Positivo |
| `CODE_GENDER` | Dado pessoal comum, **com risco discriminatório** | Declarado | **A** (fora do modelo) | **Não é dado sensível** pelo art. 5º, II. É excluído da decisão pelo princípio da não discriminação (art. 6º, IX) e mantido apenas para auditoria de viés (§4) |
| `DAYS_BIRTH` → `AGE_YEARS` | Dado pessoal comum, **com risco discriminatório** | Declarado | M | Preditor relevante de risco e uso usual em crédito. Por ser característica protegida contra discriminação, o uso é auditado (§4) |
| `CNT_CHILDREN` | Dado pessoal comum | Declarado | M | Composição familiar afeta a capacidade de pagamento. Possível *proxy* de gênero: auditado (§4) |
| `NAME_FAMILY_STATUS` | Dado pessoal comum | Declarado | M | Idem. Possível *proxy* de gênero e idade: auditado (§4) |
| `NAME_EDUCATION_TYPE` | Dado pessoal comum | Declarado | M | Preditor socioeconômico |
| `AMT_INCOME_TOTAL` | Dado pessoal comum (financeiro) | Declarado | M | Capacidade de pagamento |
| `NAME_INCOME_TYPE`, `DAYS_EMPLOYED` → `YEARS_EMPLOYED`, `FLAG_EMPLOYED_ANOMALY` | Dado pessoal comum | Declarado / derivado | M | Estabilidade de renda |
| `AMT_CREDIT`, `AMT_ANNUITY`, `AMT_GOODS_PRICE`, `NAME_CONTRACT_TYPE` | Dado pessoal comum (da operação) | Da solicitação | M | Características do crédito solicitado |
| `FLAG_OWN_CAR`, `FLAG_OWN_REALTY` | Dado pessoal comum (patrimonial) | Declarado | M | Indicadores patrimoniais |
| `REGION_RATING_CLIENT` | Dado pessoal comum (agregado regional) | Atribuído | M | Risco regional. Possível *proxy* socioeconômico: monitorado |
| `EXT_SOURCE_1/2/3` | Dado pessoal de **terceiros** (bureaus) | Compartilhado | M | Scores externos. Compartilhamento amparado na proteção do crédito (art. 7º, X) e na Lei do Cadastro Positivo |
| `CREDIT_INCOME_RATIO`, `ANNUITY_INCOME_RATIO`, `ANNUITY_CREDIT_RATIO` | Dado pessoal derivado | Calculado | M | Comprometimento de renda: derivados de dados já necessários, sem nova coleta |
| `SCORE`, `APROVADO` | **Dado pessoal inferido** | Gerado pelo modelo | Saída | É a base da decisão automatizada. Sujeito ao art. 20 (revisão e explicação dos critérios) |

**Dados pessoais sensíveis (art. 5º, II):** nenhum na seleção. As colunas descartadas na ingestão também não contêm origem racial, religião, opinião política, filiação sindical, saúde, vida sexual, dado genético ou biométrico.

## 1.4 Mapa de armazenamento

| Local | Nível | Contém dado pessoal? | Versionado no Git? | Controle |
|---|---|---|---|---|
| `data/raw/` | Linha (21 de 122 colunas usadas) | Sim | **Não** (`.gitignore`) | Acesso restrito ao ambiente de dados |
| `data/reference/` | Linha | Sim | Não | Idem |
| `data/production/incoming/`, `accepted/`, `scored/`, `labels/` | Linha | Sim (inclui score inferido) | Não | Idem |
| `data/quarantine/` | Linha + valores reprovados (`_failures.csv`) | **Sim** | Não | Retenção curta (§3). É o ponto de maior exposição |
| `models/baseline.joblib` | Parâmetros do modelo | Não diretamente | Não | Registrado no MLflow com versão |
| `logs/pipeline.jsonl` | Agregado (contagens, métricas, nomes de regras) | **Não**, garantido por teste (`test_log_nao_contem_valores_de_clientes`) | Não | Pode ser enviado a ferramentas de observabilidade |
| `reports/*.json`, `*.csv`, `*.md` | Agregado | Não | Sim (público) | — |
| `reports/drift/*.html` | Agregado (histogramas) | Não: sem ID e sem gênero no conjunto enviado ao Evidently, verificado por busca | Sim (público) | — |
| `docs/` | Agregado | Não, após a correção da descrição individual do EDA | Sim (público) | — |
| `mlflow.db`, `mlruns/` | Métricas agregadas + modelo + eventos | Não | Não | — |

## 1.5 Correções feitas durante o inventário

| Achado | Ação |
|---|---|
| `eda_findings.md` descrevia um indivíduo específico (combinação de renda, crédito, parcela e inadimplência), em repositório público | Descrição generalizada |
| Garantia de "log sem dados pessoais" existia só por desenho | Convertida em teste automatizado |
| `CODE_GENDER` estava documentado como "atributo sensível" | Reclassificado: dado comum com risco discriminatório (art. 6º, IX), não dado sensível (art. 5º, II) |
