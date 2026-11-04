# Achados da EDA — Referência (`data/reference/train.parquet`)

> Escopo: 184.506 linhas (60% do `application_train.csv`, split estratificado, seed 42).
> A EDA foi feita **somente na referência**; o pool de produção não foi inspecionado.

## Tipos de regra

| Tipo | Significado | Efeito no pipeline |
|---|---|---|
| **Rígida** | Valor impossível | Viola → lote bloqueado e enviado para `data/quarantine/` |
| **Alerta** | Valor improvável, mas possível | Viola → registra em log e deixa passar |
| **Transformação** | Código disfarçado de valor | Tratado no pré-processamento, antes da validação |

## Achados e regras candidatas

| # | Coluna(s) | Achado | Regra candidata | Tipo |
|---|---|---|---|---|
| Q1 | `TARGET` | Taxa de default de 8,07% | Domínio {0, 1} | Rígida |
| Q2 | `EXT_SOURCE_1`, `EXT_SOURCE_3` | 56,4% e 19,8% de nulos (nulo estrutural: bureau sem score) | % de nulos ≤ referência + margem | Alerta |
| Q2 | `EXT_SOURCE_2` | 0,2% de nulos | % de nulos ≤ referência + margem | Alerta |
| Q2 | `AMT_ANNUITY` | Nulos residuais (<0,01%) | Não nulo (contrato sem parcela é inválido) | Rígida |
| Q2 | `AMT_GOODS_PRICE` | 0,08% de nulos | Não nulo quando `NAME_CONTRACT_TYPE = Cash loans` *(pendente: confirmar que os nulos são todos `Revolving loans`)* | Rígida (condicional) |
| Q2 | `EXT_SOURCE_1/2/3` | Min ≈ 0, máx ≈ 0,95 | Entre 0 e 1 | Rígida |
| Q3 | `DAYS_EMPLOYED` | 17,9% com valor 365243; todos os positivos são essa sentinela | ≤ 0 ou == 365243 | Rígida |
| Q3 | `DAYS_EMPLOYED` | Sentinela tem default de 5,3% vs 8,7% → carrega informação | Criar flag binária + converter a sentinela em NaN | Transformação |
| Q3 | `DAYS_EMPLOYED` × `NAME_INCOME_TYPE` | Sentinela ⇒ Pensioner (33.044) ou Unemployed (12); 8 pensionistas têm dias reais | Sentinela implica `NAME_INCOME_TYPE ∈ {Pensioner, Unemployed}` | Alerta |
| Q3 | `DAYS_EMPLOYED` × `DAYS_BIRTH` | 0 violações | Tempo de emprego < idade (exceto sentinela) | Rígida |
| Q4 | `DAYS_BIRTH` | Idade de 21,0 a 69,0 anos | Idade entre 18 e 100 anos | Rígida |
| Q4 | `DAYS_BIRTH` | Range observado | Idade entre 21 e 70 anos | Alerta |
| Q5 | `AMT_INCOME_TOTAL` | Mínimo de 25.650, sem zeros | > 0 e não nulo | Rígida |
| Q5 | `AMT_INCOME_TOTAL` | Máx de 117M = 130× o p99,9 (900k); linha com crédito de 562k e parcela de 26k → erro | ≤ 50.000.000 | Rígida |
| Q5 | `AMT_INCOME_TOTAL` | 18M e 9M coerentes com crédito/parcela → legítimos | > 1.000.000 | Alerta |
| Q6 | `CODE_GENDER` | 1 linha `XNA`; coluna fora do modelo (só auditoria de viés) | Domínio {F, M, XNA}; `XNA` gera alerta | Alerta |
| Q6 | `NAME_FAMILY_STATUS` | 1 linha `Unknown` | Domínio fechado (6 valores observados); `Unknown` gera alerta | Rígida (domínio) + Alerta |
| Q6 | `NAME_INCOME_TYPE` | 8 categorias, raras legítimas (Student 6, Maternity leave 2) | Domínio fechado (8 valores observados) | Rígida |
| Q6 | `NAME_EDUCATION_TYPE` | 5 categorias limpas | Domínio fechado (5 valores observados) | Rígida |
| Q6 | `NAME_CONTRACT_TYPE`, `FLAG_OWN_CAR`, `FLAG_OWN_REALTY` | Binárias limpas | Domínio fechado | Rígida |
| Q6 | `REGION_RATING_CLIENT` | Valores 1 a 3 | Domínio {1, 2, 3} | Rígida |
| Q6 | `CNT_CHILDREN` | 0 a 19 | Inteiro entre 0 e 25 | Rígida |
| Q6 | `CNT_CHILDREN` | Valores altos raros | > 10 | Alerta |
| Q7 | `SK_ID_CURR` | 0 duplicatas | Único por lote (protege contra reprocessamento) | Rígida |
| Bônus | `AMT_ANNUITY` × `AMT_CREDIT` | 0 violações | Parcela < crédito | Rígida |
| Bônus | `AMT_GOODS_PRICE` × `AMT_CREDIT` | 0,09% com bem > crédito (possível entrada à vista) | Bem > crédito | Alerta |

## Limpeza da referência
- Remover linhas que violam regras rígidas (ex.: renda de 117M).
- Aplicar a transformação de `DAYS_EMPLOYED` (flag + NaN).
- Converter `DAYS_BIRTH` e `DAYS_EMPLOYED` para anos.

## Implicações para o modelo

- **Métrica principal:** AUC e KS (padrão de crédito); Gini = 2·AUC − 1.
- **Métrica secundária:** PR-AUC, por causa do desbalanceamento (8,07% de positivos).
- **Acurácia descartada:** prever "nunca inadimple" acertaria ~92%.
- **Desbalanceamento:** `scale_pos_weight` ≈ 11,4 no XGBoost.
- **Categorias raras:** exigirão agrupamento nos testes qui-quadrado de drift (Etapa 2).

## Implicações para governança

- `CODE_GENDER` excluído do modelo e mantido apenas para auditoria de viés.
- Regras sobre `CODE_GENDER` são somente de alerta: uma coluna fora da decisão não pode bloquear uma concessão.
