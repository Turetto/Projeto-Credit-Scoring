# Relatório de alertas

- Execução: `20261115T021910-d5487d`
- Política: `v2` (limites em `src/credit_scoring/monitoring/policy.py`; limites de fairness em `reports/fairness_baseline.json`)
- Gerado em: 2026-11-15T02:19:14+00:00
- Total: 36 alertas (22 ALERTA, 14 ATENÇÃO)

## Visão da operação (pior severidade por origem, no mês em que ficou conhecida)

| conhecido_em   | execucao   | contrato   | data_drift   | prediction_drift   | fairness   | performance   |
|:---------------|:-----------|:-----------|:-------------|:-------------------|:-----------|:--------------|
| mes_00         | ESTÁVEL    | ESTÁVEL    | ESTÁVEL      | ESTÁVEL            | ESTÁVEL    | ESTÁVEL       |
| mes_01         | ESTÁVEL    | ESTÁVEL    | ESTÁVEL      | ESTÁVEL            | ESTÁVEL    | ESTÁVEL       |
| mes_02         | ESTÁVEL    | ESTÁVEL    | ATENÇÃO      | ESTÁVEL            | ESTÁVEL    | ESTÁVEL       |
| mes_03         | ESTÁVEL    | ATENÇÃO    | ALERTA       | ESTÁVEL            | ESTÁVEL    | ESTÁVEL       |
| mes_04         | ESTÁVEL    | ESTÁVEL    | ALERTA       | ESTÁVEL            | ESTÁVEL    | ESTÁVEL       |
| mes_05         | ESTÁVEL    | ESTÁVEL    | ALERTA       | ESTÁVEL            | ESTÁVEL    | ALERTA        |
| mes_06         | ESTÁVEL    | ESTÁVEL    | ALERTA       | ESTÁVEL            | ATENÇÃO    | ALERTA        |
| flush          | ESTÁVEL    | ESTÁVEL    | ESTÁVEL      | ESTÁVEL            | ALERTA     | ALERTA        |

`flush` = rótulos que, em tempo real, ainda não teriam amadurecido.

## Notificações (somente escaladas)

16 notificações de 36 alertas registrados.

| conhecido_em   | origem      | severidade   | regra                                    |   valor |
|:---------------|:------------|:-------------|:-----------------------------------------|--------:|
| mes_02         | data_drift  | ATENÇÃO      | PSI ANNUITY_CREDIT_RATIO                 |  0.1346 |
| mes_03         | contrato    | ATENÇÃO      | linhas em quarentena                     |  1.0000 |
| mes_03         | data_drift  | ALERTA       | PSI ANNUITY_CREDIT_RATIO                 |  0.4258 |
| mes_03         | data_drift  | ATENÇÃO      | PSI AMT_ANNUITY                          |  0.1128 |
| mes_03         | data_drift  | ATENÇÃO      | PSI AMT_INCOME_TOTAL                     |  0.1985 |
| mes_04         | data_drift  | ATENÇÃO      | PSI AMT_CREDIT                           |  0.1184 |
| mes_05         | data_drift  | ALERTA       | PSI AMT_ANNUITY                          |  0.2931 |
| mes_05         | data_drift  | ALERTA       | PSI AMT_GOODS_PRICE                      |  0.8927 |
| mes_05         | data_drift  | ALERTA       | PSI AMT_INCOME_TOTAL                     |  0.2738 |
| mes_05         | data_drift  | ATENÇÃO      | PSI ANNUITY_INCOME_RATIO                 |  0.1095 |
| mes_05         | performance | ALERTA       | queda de AUC                             |  0.0515 |
| mes_05         | performance | ALERTA       | gap de calibração                        |  0.0226 |
| mes_06         | data_drift  | ATENÇÃO      | PSI AGE_YEARS                            |  0.1080 |
| mes_06         | data_drift  | ATENÇÃO      | PSI EXT_SOURCE_2                         |  0.1121 |
| mes_06         | fairness    | ATENÇÃO      | dispersão de calibração por faixa etária |  0.0418 |
| flush          | fairness    | ALERTA       | dispersão de calibração por faixa etária |  0.0572 |

## Detalhe

| lote   | conhecido_em   | origem      | severidade   | regra                                    |   valor | acao                                                                                                                                      |
|:-------|:---------------|:------------|:-------------|:-----------------------------------------|--------:|:------------------------------------------------------------------------------------------------------------------------------------------|
| mes_02 | mes_02         | data_drift  | ATENÇÃO      | PSI ANNUITY_CREDIT_RATIO                 |  0.1346 | Acompanhar no próximo lote e analisar os segmentos afetados.                                                                              |
| mes_03 | mes_03         | data_drift  | ALERTA       | PSI ANNUITY_CREDIT_RATIO                 |  0.4258 | Abrir análise causal (playbook de governança) e avaliar recalibração do score.                                                            |
| mes_03 | mes_03         | contrato    | ATENÇÃO      | linhas em quarentena                     |  1.0000 | Revisar as linhas em data/quarantine/; corrigir na origem ou descartar.                                                                   |
| mes_03 | mes_03         | data_drift  | ATENÇÃO      | PSI AMT_ANNUITY                          |  0.1128 | Acompanhar no próximo lote e analisar os segmentos afetados.                                                                              |
| mes_03 | mes_03         | data_drift  | ATENÇÃO      | PSI AMT_INCOME_TOTAL                     |  0.1985 | Acompanhar no próximo lote e analisar os segmentos afetados.                                                                              |
| mes_04 | mes_04         | data_drift  | ALERTA       | PSI ANNUITY_CREDIT_RATIO                 |  0.6940 | Abrir análise causal (playbook de governança) e avaliar recalibração do score.                                                            |
| mes_04 | mes_04         | data_drift  | ATENÇÃO      | PSI AMT_ANNUITY                          |  0.1903 | Acompanhar no próximo lote e analisar os segmentos afetados.                                                                              |
| mes_04 | mes_04         | data_drift  | ATENÇÃO      | PSI AMT_CREDIT                           |  0.1184 | Acompanhar no próximo lote e analisar os segmentos afetados.                                                                              |
| mes_05 | mes_05         | data_drift  | ALERTA       | PSI AMT_ANNUITY                          |  0.2931 | Abrir análise causal (playbook de governança) e avaliar recalibração do score.                                                            |
| mes_05 | mes_05         | data_drift  | ALERTA       | PSI AMT_GOODS_PRICE                      |  0.8927 | Abrir análise causal (playbook de governança) e avaliar recalibração do score.                                                            |
| mes_05 | mes_05         | data_drift  | ALERTA       | PSI AMT_INCOME_TOTAL                     |  0.2738 | Abrir análise causal (playbook de governança) e avaliar recalibração do score.                                                            |
| mes_05 | mes_05         | data_drift  | ALERTA       | PSI ANNUITY_CREDIT_RATIO                 |  0.9335 | Abrir análise causal (playbook de governança) e avaliar recalibração do score.                                                            |
| mes_02 | mes_05         | performance | ALERTA       | queda de AUC                             |  0.0515 | Degradação confirmada por rótulos: recalibrar ou retreinar; revisar o corte com Risco.                                                    |
| mes_02 | mes_05         | performance | ALERTA       | gap de calibração                        |  0.0226 | Degradação confirmada por rótulos: recalibrar ou retreinar; revisar o corte com Risco.                                                    |
| mes_05 | mes_05         | data_drift  | ATENÇÃO      | PSI AMT_CREDIT                           |  0.1027 | Acompanhar no próximo lote e analisar os segmentos afetados.                                                                              |
| mes_05 | mes_05         | data_drift  | ATENÇÃO      | PSI ANNUITY_INCOME_RATIO                 |  0.1095 | Acompanhar no próximo lote e analisar os segmentos afetados.                                                                              |
| mes_06 | mes_06         | data_drift  | ALERTA       | PSI AMT_ANNUITY                          |  0.4361 | Abrir análise causal (playbook de governança) e avaliar recalibração do score.                                                            |
| mes_06 | mes_06         | data_drift  | ALERTA       | PSI AMT_GOODS_PRICE                      |  0.6273 | Abrir análise causal (playbook de governança) e avaliar recalibração do score.                                                            |
| mes_06 | mes_06         | data_drift  | ALERTA       | PSI AMT_INCOME_TOTAL                     |  0.2921 | Abrir análise causal (playbook de governança) e avaliar recalibração do score.                                                            |
| mes_06 | mes_06         | data_drift  | ALERTA       | PSI ANNUITY_CREDIT_RATIO                 |  0.8936 | Abrir análise causal (playbook de governança) e avaliar recalibração do score.                                                            |
| mes_03 | mes_06         | performance | ALERTA       | queda de AUC                             |  0.0363 | Degradação confirmada por rótulos: recalibrar ou retreinar; revisar o corte com Risco.                                                    |
| mes_03 | mes_06         | performance | ALERTA       | gap de calibração                        |  0.0283 | Degradação confirmada por rótulos: recalibrar ou retreinar; revisar o corte com Risco.                                                    |
| mes_06 | mes_06         | data_drift  | ATENÇÃO      | PSI AGE_YEARS                            |  0.1080 | Acompanhar no próximo lote e analisar os segmentos afetados.                                                                              |
| mes_06 | mes_06         | data_drift  | ATENÇÃO      | PSI AMT_CREDIT                           |  0.1980 | Acompanhar no próximo lote e analisar os segmentos afetados.                                                                              |
| mes_06 | mes_06         | data_drift  | ATENÇÃO      | PSI ANNUITY_INCOME_RATIO                 |  0.1849 | Acompanhar no próximo lote e analisar os segmentos afetados.                                                                              |
| mes_06 | mes_06         | data_drift  | ATENÇÃO      | PSI EXT_SOURCE_2                         |  0.1121 | Acompanhar no próximo lote e analisar os segmentos afetados.                                                                              |
| mes_03 | mes_06         | fairness    | ATENÇÃO      | dispersão de calibração por faixa etária |  0.0418 | Disparidade mudou em relação à linha de base documentada: acionar Compliance e aplicar o gate de fairness antes de qualquer recalibração. |
| mes_04 | flush          | performance | ALERTA       | queda de AUC                             |  0.0767 | Degradação confirmada por rótulos: recalibrar ou retreinar; revisar o corte com Risco.                                                    |
| mes_04 | flush          | performance | ALERTA       | gap de calibração                        |  0.0321 | Degradação confirmada por rótulos: recalibrar ou retreinar; revisar o corte com Risco.                                                    |
| mes_04 | flush          | fairness    | ALERTA       | dispersão de calibração por faixa etária |  0.0572 | Disparidade mudou em relação à linha de base documentada: acionar Compliance e aplicar o gate de fairness antes de qualquer recalibração. |
| mes_05 | flush          | performance | ALERTA       | queda de AUC                             |  0.0983 | Degradação confirmada por rótulos: recalibrar ou retreinar; revisar o corte com Risco.                                                    |
| mes_05 | flush          | performance | ALERTA       | gap de calibração                        |  0.0344 | Degradação confirmada por rótulos: recalibrar ou retreinar; revisar o corte com Risco.                                                    |
| mes_06 | flush          | performance | ALERTA       | queda de AUC                             |  0.0803 | Degradação confirmada por rótulos: recalibrar ou retreinar; revisar o corte com Risco.                                                    |
| mes_06 | flush          | performance | ALERTA       | gap de calibração                        |  0.0439 | Degradação confirmada por rótulos: recalibrar ou retreinar; revisar o corte com Risco.                                                    |
| mes_06 | flush          | fairness    | ALERTA       | dispersão de calibração por faixa etária |  0.0631 | Disparidade mudou em relação à linha de base documentada: acionar Compliance e aplicar o gate de fairness antes de qualquer recalibração. |
| mes_05 | flush          | fairness    | ATENÇÃO      | dispersão de calibração por faixa etária |  0.0362 | Disparidade mudou em relação à linha de base documentada: acionar Compliance e aplicar o gate de fairness antes de qualquer recalibração. |
