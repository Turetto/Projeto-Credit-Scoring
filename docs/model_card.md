# Model Card — `credit-scoring-baseline` v1

Formato inspirado em Mitchell et al. (2019), *Model Cards for Model Reporting*.

## Detalhes do modelo

| Item | Valor |
|---|---|
| Tipo | XGBoost (classificação binária) em pipeline scikit-learn |
| Versão | 1 (MLflow Model Registry: `credit-scoring-baseline`) |
| Saída | Probabilidade de inadimplência (PD); aprovação se PD < 0,0867 (threshold no KS máximo) |
| Seleção | Venceu a regressão logística por +1,84 p.p. de AUC em validação cruzada 5-fold; regra fixada antes: o XGBoost só vence com ganho ≥ 1 p.p. |
| Hiperparâmetros | 400 árvores, `learning_rate` 0,05, profundidade 4, `subsample` e `colsample_bytree` 0,8; sem tuning (baseline) |
| Código | `src/credit_scoring/model/train.py` |

## Uso pretendido

- **Uso:** apoio à decisão de concessão de crédito pessoal (*cash loans* e rotativo), com revisão humana disponível sob pedido do titular (art. 20 da LGPD).
- **Usuários:** área de crédito e risco de uma fintech.
- **Fora do escopo:** decisões sem possibilidade de revisão; populações ou produtos diferentes dos do treino; uso do score para fins não relacionados a crédito.

## Dados

| Conjunto | Origem | Linhas | Observações |
|---|---|---|---|
| Treino | Home Credit Default Risk (Kaggle), 60% estratificado | 184.498 | Após limpeza via contrato (8 linhas removidas) |
| Teste | 15% estratificado | 46.125 | Usado uma única vez para reportar métricas |
| Produção simulada | 25% restantes, em 7 lotes de 4.000 | — | Com choque macroeconômico injetado |

**Features (21):** valores da operação (crédito, parcela, bem, modalidade), renda e emprego, perfil (idade, filhos, estado civil, escolaridade, posse de carro e imóvel), região, três scores externos de bureau e três razões de comprometimento. Gênero **não** é feature (mantido só para auditoria). Detalhes: `docs/governanca/01_inventario_dados.md`.

## Métricas (teste)

| Métrica | Valor |
|---|---|
| AUC | 0,7596 |
| Gini | 0,519 |
| KS | 0,391 |
| PR-AUC | 0,246 |
| Brier | 0,0677 (modelo ingênuo: 0,0742) |
| PD média prevista × default observado | 8,06% × 8,07% |
| Taxa de aprovação | 69,2% |
| Inadimplência dos aprovados | 3,9% |

## Análise por grupo (fairness)

| Grupo | Aprovação | AIR | Gap de calibração | AUC |
|---|---|---|---|---|
| Mulheres | 72,3% | 1,00 | −0,46 p.p. | 0,758 |
| Homens | 63,4% | 0,88 | +0,91 p.p. | 0,754 |
| 18–29 anos | 50,0% | **0,57** | −0,16 p.p. | 0,750 |
| 30–44 anos | 64,3% | **0,74** | −0,11 p.p. | 0,762 |
| 45–59 anos | 77,5% | 0,89 | +0,04 p.p. | 0,750 |
| 60+ anos | 87,1% | 1,00 | +0,56 p.p. | 0,707 |

O modelo é calibrado em todos os grupos: as diferenças de aprovação acompanham diferenças reais de inadimplência. A igualdade de oportunidade não é atendida para os jovens (bons pagadores de 18–29 aprovados em 54%, contra 88% em 60+). Análise completa, trade-offs e decisões: `docs/governanca/04_auditoria_vies.md`.

## Explicabilidade

- **Fatores de maior peso:** scores de bureau (42,5% somados), valor do bem (9,5%), parcela/crédito (8,5%), tempo de emprego (6,8%).
- **Motivos individuais:** os 3 fatores que mais aumentaram a PD, via TreeSHAP nativo do XGBoost, com fidelidade verificada (erro máximo de 6·10⁻⁷).
- Detalhes: `docs/governanca/02_base_legal_explicabilidade.md`.

## Monitoramento

O modelo é monitorado pelo pipeline do projeto: contrato de dados na entrada, data drift (PSI por quantis e KS), prediction drift, performance com atraso de rótulos de 3 meses, e fairness (queda de AIR e dispersão de calibração). Limites em `src/credit_scoring/monitoring/policy.py` e `reports/fairness_baseline.json`; catálogo em `docs/catalogo_metricas.md`.

## Limitações e riscos conhecidos

| Limitação | Efeito |
|---|---|
| Dependência de scores de terceiros (42,5% da decisão) | A explicação ao titular é incompleta sem encaminhamento ao bureau |
| Sensibilidade a choques macroeconômicos | Valor do bem, parcela e parcela/crédito (~24% da decisão) são expostos a inflação e juros. Na simulação, a AUC caiu para 0,68 e o modelo passou a subestimar o risco em até 4,4 p.p. |
| Cegueira a concept drift sem rótulos | Desemprego pós-concessão não aparece nas features; o PSI do score ficou estável enquanto a inadimplência dos aprovados dobrou |
| Discriminação menor para 60+ | AUC de 0,707 nesse grupo |
| Disparidade de oportunidade para jovens | Decisão normativa encaminhada a Risco e Compliance, com custo quantificado |
| Dados de origem estrangeira | O Home Credit não representa a população brasileira; os resultados demonstram o método, não um modelo pronto para o mercado brasileiro |

## Considerações éticas e de governança

- Gênero excluído da decisão, mas reconstituível pelas features (AUC 0,808); a exclusão não é tratada como garantia de não discriminação.
- A remoção da idade foi testada e descartada: piorou a disparidade para os jovens.
- Toda nova versão passa pelo *gate* de qualidade e fairness descrito em `docs/governanca/05_causalidade_playbook.md`.
