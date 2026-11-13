# Catálogo de métricas de monitoramento

Fonte única dos limites: `src/credit_scoring/monitoring/policy.py` (política **v2**).
Fonte única dos dados: `logs/pipeline.jsonl` (eventos estruturados, um por etapa e lote).
Destinos: MLflow (`credit-scoring-monitoramento`, uma run por execução, `step = mês`) e `reports/alerts_latest.md`.

## Níveis de severidade

| Nível | Código no MLflow | Significado | Resposta esperada |
|---|---|---|---|
| ESTÁVEL | 0 | Dentro do esperado | Nenhuma |
| ATENÇÃO | 1 | Mudança detectada, ainda sem impacto confirmado | Acompanhar no próximo lote; analisar segmentos |
| ALERTA | 2 | Mudança relevante ou degradação confirmada | Agir conforme a coluna "Ação" |

## 1. Execução do pipeline

| Métrica | Campo do evento | Chave no MLflow | Definição | Limite | Ação |
|---|---|---|---|---|---|
| Status da etapa | `status` (toda etapa) | `execucoes_<etapa>_<status>` | SUCESSO ou FALHA, com `erro` e `mensagem` em caso de falha | FALHA → ALERTA imediato | Ver o log da etapa; reexecutar o lote após a correção |
| Duração por etapa | `duracao_ms` | `gate_duracao_ms`, `scoring_duracao_ms` | Tempo de execução da etapa por lote | Monitorado, sem alerta automático. Referência observada: 40–140 ms por lote de 4.000 linhas | Investigar se ficar uma ordem de grandeza acima da referência |
| Volume de entrada | `linhas_entrada` | `gate_linhas_entrada` | Linhas recebidas no lote | Monitorado, sem alerta automático | Queda brusca indica falha no sistema de origem |

## 2. Qualidade de dados (contrato)

| Métrica | Campo do evento | Chave no MLflow | Definição | Limite | Ação |
|---|---|---|---|---|---|
| Status do gate | `status` (`contract_gate`) | `gate_bloqueado` | ACEITO / ACEITO_COM_QUARENTENA / BLOQUEADO | Quarentena → ATENÇÃO; bloqueio → ALERTA | Bloqueio: acionar o responsável pela origem; não reprocessar sem correção |
| Taxa de rejeição | `taxa_rejeicao` | `gate_taxa_rejeicao` | Linhas reprovadas em regras rígidas ÷ linhas do lote | > 1% (`MAX_TAXA_REJEICAO`) → lote bloqueado | Erro sistêmico na origem |
| Violações por regra | `regras_violadas` | (artefato de eventos) | Linhas únicas por regra rígida (`coluna:regra`) | Qualquer violação estrutural → bloqueio | Ver `data/quarantine/<lote>_failures.csv` |
| Alertas de contrato | `alertas` | (artefato de eventos) | Linhas que violam regras de alerta (não bloqueiam) | Monitorado | Indício precoce de mudança (ex.: renda > 1M cresce com a inflação) |

## 3. Drift (sem rótulos, disponível no mês)

| Métrica | Campo do evento | Chave no MLflow | Definição | Limite | Ação |
|---|---|---|---|---|---|
| PSI por feature | `psi` | `psi_<feature>` | PSI com 10 bins por quantis da referência (`test_scored`); categóricas por categoria | ≥ 0,10 ATENÇÃO · ≥ 0,25 ALERTA | ATENÇÃO: acompanhar · ALERTA: abrir análise causal, avaliar recalibração |
| Materialidade nominal | `delta_mediana`, `imateriais` | `delta_mediana_<feature>`, `drift_n_imateriais` | Variação relativa da mediana nas variáveis `AMT_*` | Para `AMT_*`, só alerta se \|Δ mediana\| ≥ 5% | Mudança estatística sem relevância econômica fica registrada, sem alerta |
| Intensidade do drift | `ks_d` | `ks_d_<feature>` | Estatística D do Kolmogorov-Smirnov (sem bins) | Sem alerta (medida de intensidade) | Usar para comparar magnitude entre meses |
| Prediction drift | `psi_score`, `status_score` | `psi_SCORE`, `drift_nivel_score` | PSI da distribuição de PD prevista | ≥ 0,10 ATENÇÃO · ≥ 0,25 ALERTA | Revisar taxa de aprovação e corte com Risco |
| Nível de drift | `status_drift` | `drift_nivel` | Pior nível entre as features | — | Resumo para o painel |

## 4. Performance (com atraso de rótulos)

Rótulos amadurecem com `LAG_ROTULOS = 3` meses: a performance do mês *t* é conhecida no mês *t + 3*. Cada métrica tem duas séries no MLflow: no mês da ocorrência (`perf_*`) e no mês do conhecimento (`operacao_*`).

| Métrica | Campo do evento | Chave no MLflow | Definição | Limite | Ação |
|---|---|---|---|---|---|
| AUC | `auc`, `queda_auc` | `perf_auc`, `perf_nivel_auc`, `operacao_nivel_auc` | AUC no lote vs referência (0,7596) | Queda ≥ 2 p.p. ATENÇÃO · ≥ 3 p.p. ALERTA | Recalibrar ou retreinar |
| Gap de calibração | `gap_calibracao` | `perf_gap_calibracao`, `perf_nivel_calibracao`, `operacao_nivel_calibracao` | Default observado − PD média prevista (> 0 = modelo subestima o risco) | \|gap\| ≥ 1 p.p. ATENÇÃO · ≥ 2 p.p. ALERTA | Recalibrar; revisar corte com Risco |
| Default observado | `default_observado` | `perf_default_observado` | Taxa de inadimplência do lote | Monitorado | Contexto para o gap |

## 5. Negócio

| Métrica | Campo do evento | Chave no MLflow | Definição | Limite | Ação |
|---|---|---|---|---|---|
| Taxa de aprovação | `taxa_aprovacao` | `scoring_taxa_aprovacao` | Proporção com PD < threshold KS (0,0867) | Monitorado; limite definido pela área de Risco | Mudança brusca exige revisão do corte |
| Inadimplência da carteira aprovada | `default_aprovados` | `perf_default_aprovados` | Default entre os aprovados | Monitorado; referência 3,9% | Principal métrica para a diretoria |
| PD média prevista | `pd_media` | `scoring_pd_media` | Média do score no lote | Monitorado; referência 0,0806 | Comparar com o default observado quando os rótulos chegarem |

## Valores de referência (baseline)

| Métrica | Valor | Origem |
|---|---|---|
| AUC | 0,7596 | Teste da 1.4 |
| KS | 0,3913 | Teste da 1.4 |
| PD média prevista | 0,0806 | Teste da 1.4 |
| Default observado | 0,0807 | Teste da 1.4 |
| Taxa de aprovação | 69,2% | Teste da 1.4 |
| Inadimplência dos aprovados | 3,9% | Teste da 1.4 |

## Política de notificação

O relatório registra **todos** os alertas (auditoria). Uma **notificação** (o que interrompe uma pessoa) só é emitida quando:

1. uma combinação (origem, regra) aparece pela primeira vez; ou
2. o nível dessa combinação sobe em relação ao mês anterior; ou
3. a combinação some e volta (regressão após melhora).

Alertas que se repetem no mesmo nível não geram nova notificação. Objetivo: evitar fadiga de alertas.

## Versões da política

| Versão | Etapa | Mudança | Evidência |
|---|---|---|---|
| v1 | 2.1 | PSI 0,10/0,25; queda de AUC 2/3 p.p.; gap 1/2 p.p. | Fixada antes da simulação |
| v1 (validação) | 2.5 | Métrica de decisão passa a ser o PSI por quantis (não o do Evidently) | Evidently subestimou drift em variáveis monetárias de cauda longa; PSI por quantis com 0% de falso alarme sob H0 (n = 4.000) |
| v2 | 3.5 | Materialidade de 5% na mediana para variáveis `AMT_*` | Renda +1,8% nominal gerou PSI 0,18 por heaping; mudança estatisticamente real, economicamente irrelevante |

## Limitações conhecidas

- Os limites de PSI foram validados para lotes de **4.000 linhas**. Lotes menores exigem recalcular a distribuição nula.
- A AUC de um lote de 4.000 linhas tem IC 95% de cerca de ±2,6 p.p. Decisões baseadas em um único mês são frágeis.
- Em variáveis com heaping (`ANNUITY_CREDIT_RATIO`, `AMT_GOODS_PRICE`), o PSI detecta corretamente, mas sua **magnitude** não é monotônica no choque. Para comparar intensidade, use o KS D.
- Duração e volume são monitorados sem alerta automático.
- O prediction drift não detecta concept drift: o score permaneceu estável enquanto a inadimplência dos aprovados dobrou. A performance com rótulos é indispensável.
