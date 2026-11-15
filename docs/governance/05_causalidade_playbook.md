# 5. Análise causal e playbook de resposta

## 5.1 A pergunta causal

Detectar a degradação (Etapas 2 e 3) responde **"o modelo piorou?"**. A análise causal responde **"por quê?"**, e é ela que define a ação correta: recalibrar, retreinar, ajustar a política de corte ou apenas monitorar.

## 5.2 Mecanismos injetados (gabarito)

A simulação aplicou quatro mecanismos cumulativos (`reports/simulation_config.json`):

| Mecanismo | O que muda | Tipo de drift | Intensidade em `mes_06` |
|---|---|---|---|
| Inflação | Crédito e bem +π; renda +0,6·π (repasse parcial) | Data drift sobre variáveis nominais | π = 25% |
| Aperto monetário | Parcela +ρ para o mesmo crédito | Data drift | ρ = 15% |
| Expansão comercial | Mix mais jovem e com score de bureau menor | Covariate shift (P(y\|X) preservado por construção) | Idade média 43,9 → 40,0 |
| Desemprego pós-concessão | Assalariados com maior comprometimento passam a inadimplir | **Concept drift** (P(y\|X) muda; invisível nas features) | δ = 5% |

## 5.3 Evidência 1 — ablação contrafactual pareada

Os mesmos clientes e scores de cada mês foram avaliados com os rótulos simulados (com desemprego) e com os rótulos originais (sem desemprego). Como as features são idênticas, a diferença isola o efeito do desemprego (`drift/attribution.py`, `reports/degradation_attribution.csv`).

| Mês | Queda de AUC total | Por inflação + perfil | Por desemprego | Gap total | Gap por inflação + perfil | Gap por desemprego |
|---|---|---|---|---|---|---|
| `mes_02` | 5,2 p.p. | 4,2 | 1,0 | +2,3 p.p. | +1,3 | +0,9 |
| `mes_03` | 3,6 | −1,1 | 4,8 | +2,8 | +1,0 | +1,8 |
| `mes_04` | 7,7 | 3,4 | 4,2 | +3,2 | +0,9 | +2,3 |
| `mes_05` | 9,8 | 2,8 | 7,0 | +3,4 | +0,1 | +3,4 |
| `mes_06` | 8,0 | 1,0 | 7,0 | +4,4 | +0,5 | +3,9 |

**Conclusões:**

1. **A dinâmica tem duas fases.** Em `mes_02`–`mes_04` (**choque nominal**), inflação + perfil fazem o modelo subestimar o risco: o gap sem desemprego é positivo, com IC 95% acima de zero nesses três meses. Em `mes_05`–`mes_06` (**choque real**), o desemprego explica 71–87% da queda de AUC e 89–98% do gap.
2. **Na calibração, o efeito de inflação + perfil é robusto; na AUC, não.** O componente de AUC oscila sem acompanhar a intensidade do choque (−1,1 a +4,2 p.p.), dentro do ruído de um lote de 4.000 (IC ≈ ±2,6 p.p.).

## 5.4 Evidência 2 — canal de transmissão

A explicabilidade (documento 2) mostra **por onde** o choque entra no modelo:

| Fator | Peso na decisão | Exposição ao choque | Drift observado (PSI por quantis) |
|---|---|---|---|
| Valor do bem financiado | 9,5% | Inflação | ALERTA a partir de `mes_05` |
| Parcela em relação ao crédito | 8,5% | Juros | ALERTA a partir de `mes_03` (primeiro alerta do projeto) |
| Valor da parcela | 5,6% | Inflação + juros | ALERTA a partir de `mes_05` (PSI 0,435 em `mes_06`) |
| **Renda declarada** | **0,9%** | Inflação | ALERTA a partir de `mes_05` |

Os fatores afetados por preços e juros somam **~24% da decisão**. A renda, embora derive com a inflação, quase não pesa no modelo. **A vulnerabilidade do modelo ao choque macroeconômico está no valor do bem, na parcela e na relação parcela/crédito, não na renda.**

## 5.5 Evidência 3 — o concept drift é invisível sem rótulos

| Sinal | Usa rótulo? | Resultado |
|---|---|---|
| PSI do score (prediction drift) | Não | Máximo de 0,093: **nunca alertou** |
| Queda de AIR de aprovação (fairness) | Não | Máximo de 0,025: **nunca alertou** |
| Gap de calibração | Sim | ALERTA a partir de `mes_02` |
| Dispersão de calibração por faixa etária (fairness) | Sim | ALERTA em `mes_04` e `mes_06` |

O desemprego acontece **depois** da solicitação; nenhuma feature o registra. Os sinais que dependem só das features e do score ficaram cegos para ele. A inadimplência da carteira aprovada passou de 3,9% para 8,6% enquanto o score permanecia estável.

## 5.6 Linha do tempo da detecção (visão da operação)

| Mês real | O que a operação sabia |
|---|---|
| `mes_00`–`mes_01` | Tudo estável (controle) |
| `mes_02` | Data drift em ATENÇÃO (parcela/crédito) |
| `mes_03` | **Data drift em ALERTA**: primeiro alerta acionável |
| `mes_05` | Degradação de performance confirmada pelos rótulos (de `mes_02`) |
| `mes_06` | Degradação de fairness confirmada pelos rótulos (dispersão de calibração) |
| Sempre | Prediction drift estável |

**O data drift deu 2 meses de antecedência sobre a confirmação por rótulos.**

## 5.7 O que está provado e o que não está

| Afirmação | Status |
|---|---|
| O desemprego explica a maior parte da degradação no pico do choque | **Provado** (ablação pareada) |
| Inflação + perfil degradam a calibração nas fases iniciais | **Provado** (IC do gap exclui zero em `mes_02`–`mes_04`) |
| Inflação + perfil degradam a AUC | **Não provado** (efeito dentro do ruído) |
| A inflação, isoladamente, faz o modelo subestimar o risco | **Hipótese consistente**, não isolada. A ablação não separa inflação de perfil; isso exigiria um desenho fatorial (re-pontuar com features deflacionadas), não realizado. Indício: em `mes_02`, a PD prevista caiu (8,1% → 7,7%) enquanto o risco real subia |
| O choque entra pelo bem, pela parcela e pela parcela/crédito | **Provado** quanto à exposição (peso + drift); a contribuição causal individual de cada fator não foi isolada |

## 5.8 Como fazer esta análise em produção (sem gabarito)

Na simulação, a causa é conhecida porque foi injetada. Em produção, a atribuição exige outras fontes:

1. **Segmentação do drift e da performance**: por tipo de renda (assalariados × aposentados), faixa etária e modalidade. Um choque de desemprego aparece concentrado em assalariados, como na auditoria de fairness (§4.5 do documento 4).
2. **Indicadores macroeconômicos externos**: IPCA (inflação), Selic (juros) e taxa de desocupação (PNAD Contínua), correlacionados com as séries de PSI, gap e default por segmento.
3. **Rótulos precoces** (recomendação de maior impacto): usar o atraso de 30 dias na primeira parcela (*first payment default*) como proxy de inadimplência. O atraso da confirmação cairia de ~3 meses para ~1 mês, antecipando em até 2 meses a detecção de concept drift, hoje o ponto cego do monitoramento.
4. **Contrafactuais quando possível**: re-pontuar lotes recentes com variáveis nominais deflacionadas pelo IPCA isola o efeito puramente nominal da inflação.

---

## 5.9 Playbook de resposta

### Papéis

| Papel | Responsabilidade |
|---|---|
| **ML Eng** | Pipeline, investigação técnica, preparação de recalibração/retreino |
| **Dados (origem)** | Correção de falhas nos sistemas que enviam os lotes |
| **Risco** | Política de crédito: corte, apetite de risco, aprovação de nova versão do modelo |
| **Compliance / DPO** | Não discriminação, LGPD, aprovação quando o *gate* de fairness falha |

### Resposta por tipo de alerta

| Alerta | Gatilho | Primeira resposta | Investigação | Quem decide |
|---|---|---|---|---|
| Contrato: lote BLOQUEADO | Falha estrutural ou rejeição > 1% | Lote retido; acionar Dados | `data/quarantine/<lote>_failures.csv` | Dados (correção) → ML Eng (reprocessar) |
| Contrato: quarentena | Rejeições isoladas | Nenhuma imediata | Revisar em até 30 dias (retenção) | ML Eng |
| Data drift ATENÇÃO | PSI ≥ 0,10 (com materialidade nas `AMT_*`) | Acompanhar o próximo lote | Segmentar a feature | ML Eng |
| **Data drift ALERTA** | PSI ≥ 0,25 | **Abrir análise causal (§5.8)**; verificar se há rótulos precoces | Segmentação + indicadores macro + KS D para intensidade | ML Eng recomenda → **Risco** decide (monitorar, corte mais conservador ou recalibrar) |
| Prediction drift | PSI do score ≥ 0,10 | Revisar taxa de aprovação | Comparar a PD média com o histórico | Risco |
| **Performance ALERTA** | Queda de AUC ≥ 3 p.p. ou \|gap\| ≥ 2 p.p. | Preparar recalibração ou retreino | AUC estável + gap alto → **recalibrar**; AUC em queda → **retreinar** com dados recentes | Risco (aprova a nova versão após o *gate*) |
| Fairness ATENÇÃO/ALERTA | Queda de AIR ou dispersão acima da linha de base | Acionar Compliance | Grupo afetado; relação com o choque | **Compliance** |
| Falha de execução | Etapa com status FALHA | Ver o log; reexecutar o lote | `logs/pipeline.jsonl` (`erro`, `mensagem`) | ML Eng |

### Recalibrar × retreinar no cenário simulado

Em `mes_06`, a AUC e a calibração estão em ALERTA, o que pede **retreino**. Mas os rótulos dos meses de choque só amadurecem com 3 meses de atraso: não há dados rotulados recentes suficientes. Resposta em duas fases:

1. **Imediata:** corte mais conservador decidido por Risco, mais recalibração com os rótulos já disponíveis.
2. **Quando os rótulos amadurecerem:** retreino incluindo o período de choque, submetido ao *gate*.

### *Gate* de fairness e qualidade (antes de qualquer nova versão entrar em produção)

| # | Critério | Limite | Se falhar |
|---|---|---|---|
| 1 | AUC no período recente rotulado | Não inferior à versão atual | Bloqueia |
| 2 | \|Gap de calibração\| global | < 1 p.p. | Bloqueia |
| 3 | Queda de AIR de aprovação, por grupo, vs linha de base | ≤ 0,065 (p99 da distribuição nula) | **Exige aprovação do Compliance**, com justificativa registrada |
| 4 | Dispersão de calibração entre faixas etárias | ≤ 4,28 p.p. (p99) | Exige aprovação do Compliance |
| 5 | Explicabilidade | Teste de aditividade e cobertura de rótulos passando | Bloqueia |
| 6 | Registro | Nova versão no MLflow Model Registry; versão anterior preservada para *rollback*; linha de base de fairness atualizada e assinada | Bloqueia |

O critério 3 é a resposta à tensão identificada na auditoria de viés: recalibrar para corrigir o drift **reduz** a aprovação das faixas ativas e piora o AIR dos jovens. O *gate* não proíbe essa troca, mas exige que ela seja **decidida e registrada** por quem tem a responsabilidade, não aplicada automaticamente.

### *Rollback*

A versão anterior permanece registrada no MLflow (`credit-scoring-baseline`). Se a nova versão degradar após a implantação, retorna-se à anterior e se reabre a investigação.
