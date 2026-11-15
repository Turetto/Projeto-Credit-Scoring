# 2. Base legal e explicabilidade (art. 20)

> Documento de governança de um projeto acadêmico. As fundamentações seguem a LGPD (Lei 13.709/2018), mas, em uma operação real, exigiriam validação do encarregado (DPO) e do jurídico.

## 2.1 Base legal por finalidade (art. 7º)

| Finalidade | Base legal | Fundamentação |
|---|---|---|
| Decisão de crédito (scoring da solicitação) | Art. 7º, V + art. 7º, X | A análise é procedimento preliminar a um contrato solicitado pelo próprio titular e tem como finalidade a proteção do crédito |
| Treino do modelo com histórico | Art. 7º, X | Modelar risco a partir do histórico de adimplemento é o núcleo da proteção do crédito |
| Monitoramento contínuo (drift, performance, alertas) | Art. 7º, X + art. 6º, V (qualidade dos dados) | Um modelo degradado prejudica os titulares: na simulação, a inadimplência da carteira aprovada passou de 3,9% para 8,6%. Garantir a exatidão da decisão integra a proteção do crédito; não é finalidade nova |
| Auditoria de viés (uso de `CODE_GENDER`) | Art. 7º, IX (legítimo interesse), com balanceamento (art. 10) | Ver §2.3 |
| Uso de scores de bureaus (`EXT_SOURCE_*`) | Art. 7º, X + Lei 12.414/2011 (Cadastro Positivo) | Compartilhamento entre gestores de banco de dados e consulentes para análise de crédito |

## 2.2 Por que não consentimento

O consentimento (art. 7º, I) foi descartado como base da decisão de crédito porque:

1. é revogável a qualquer momento (art. 8º, §5º), e a revogação inviabilizaria a análise de uma solicitação que o próprio titular fez;
2. condicionar a análise ao consentimento o tornaria não livre, dada a assimetria entre solicitante e concedente;
3. existem bases específicas e adequadas (art. 7º, V e X).

## 2.3 Legítimo interesse para a auditoria de viés (art. 10)

| Etapa do teste | Avaliação |
|---|---|
| Finalidade legítima | Prevenir discriminação na decisão de crédito (art. 6º, IX) |
| Necessidade | Sem o atributo, é impossível medir disparidade de resultados entre grupos |
| Minimização | `CODE_GENDER` não entra no modelo (`AUDIT_ONLY_COLS`); é usado só para calcular métricas agregadas de disparidade |
| Balanceamento | O tratamento beneficia o próprio titular (protege contra decisão discriminatória) e não gera efeito sobre ele individualmente |
| Transparência | Informado na política de privacidade como uso para auditoria de não discriminação |

## 2.4 Art. 20 — decisões automatizadas

| Dispositivo | Exigência | Atendimento no projeto |
|---|---|---|
| *Caput* | Direito de pedir revisão de decisão tomada unicamente com base em tratamento automatizado, inclusive de perfil de crédito | Processo de revisão (§2.6) |
| §1º | Informações claras e adequadas sobre critérios e procedimentos, observados os segredos comercial e industrial | Explicação global (§2.5.2) e motivos individuais (§2.5.3). Não se divulgam pesos nem o modelo |
| §2º | Se houver recusa por segredo comercial, a ANPD pode auditar aspectos discriminatórios | Auditoria de viés (documento 4) disponível para apresentação |

**Nota:** a redação vigente do art. 20, após a Lei 13.853/2019, **não exige** que a revisão seja feita por pessoa natural. O projeto adota revisão humana como **boa prática**, não como obrigação legal.

## 2.5 Explicabilidade

### 2.5.1 Método

- Contribuições **TreeSHAP nativas do XGBoost** (`pred_contribs=True`), agregadas por feature original (as colunas one-hot de uma mesma variável são somadas).
- **Verificação de fidelidade:** a soma das contribuições reproduz a previsão do modelo com erro máximo de **6,3 · 10⁻⁷** (`tests/test_explain.py` garante a aditividade). A explicação corresponde exatamente à decisão.
- Implementação: `src/credit_scoring/model/explain.py`.

### 2.5.2 Critérios da decisão (explicação global)

Participação média de cada fator na decisão (base de teste, 46 mil solicitações):

| # | Fator | Participação |
|---|---|---|
| 1 | Score de crédito externo (bureau 3) | 17,2% |
| 2 | Score de crédito externo (bureau 2) | 16,4% |
| 3 | Valor do bem financiado | 9,5% |
| 4 | Score de crédito externo (bureau 1) | 8,8% |
| 5 | Prazo e taxa do contrato (parcela em relação ao crédito) | 8,5% |
| 6 | Tempo no emprego atual | 6,8% |
| 7 | Valor da parcela | 5,6% |
| 8 | Escolaridade | 4,5% |
| 9 | Idade | 4,0% |
| 10 | Valor do crédito solicitado | 3,9% |
| | Demais 11 fatores | 14,8% |

Tabela completa: `reports/explicabilidade_global.csv`.

### 2.5.3 Motivos individuais

Para cada solicitação recusada, são informados os **três fatores que mais aumentaram o risco estimado**, em linguagem simples. Exemplos reais (sem identificação):

| Cliente | PD | Motivos |
|---|---|---|
| A | 10,9% | Score de crédito externo (bureau 2); Tempo no emprego atual; Score de crédito externo (bureau 1) |
| B | 17,8% | Score de crédito externo (bureau 3); Valor do bem financiado; Score de crédito externo (bureau 2) |
| C | 14,3% | Score de crédito externo (bureau 1); Tempo no emprego atual; Prazo e taxa do contrato |

### 2.5.4 O que é e o que não é divulgado

| Divulgado ao titular | Não divulgado (segredo comercial) |
|---|---|
| Os três fatores que mais pesaram contra a solicitação | Pesos, coeficientes e estrutura do modelo |
| A lista de fatores considerados pelo modelo | O threshold de corte e a PD exata |
| O direito de pedir revisão e o canal para isso | Dados de outros clientes |
| Quando o motivo é um score externo: qual bureau consultar | — |

## 2.6 Processo de revisão

1. **Pedido:** o titular solicita revisão pelo canal do encarregado.
2. **Prazo de resposta:** 15 dias, adotado como referência por analogia ao art. 19, II (a LGPD não fixa prazo específico para o art. 20).
3. **Análise:** um analista de crédito recebe as contribuições completas do caso e pode confirmar ou reverter a decisão.
4. **Registro:** toda revisão é registrada (decisão original, motivos, decisão final, justificativa), atendendo à responsabilização (art. 6º, X, e art. 37).
5. **Retroalimentação:** a taxa de reversão vira métrica de monitoramento. Reversões concentradas em um fator ou segmento indicam defeito do modelo.

## 2.7 Achados e implicações

| Achado | Implicação |
|---|---|
| Scores de bureaus respondem por 42,5% da decisão | A explicação é incompleta sem encaminhar o titular ao bureau, onde ele pode contestar o dado de origem (Lei 12.414/2011) |
| Fatores afetados por preços e juros (valor do bem e parcela, nominais; parcela/crédito, sensível ao choque de juros) somam ~24% da decisão | São a principal porta de entrada do choque macroeconômico no modelo (ver análise causal, documento 5). A renda declarada pesa só 0,9% |
| Idade (9º) e escolaridade (8º) estão entre os 10 fatores | A frequência com que aparecem como **motivo de recusa** é medida na auditoria de viés (documento 4) |

## 2.8 Limitações

- O SHAP explica o **modelo**, não a causalidade do mundo real: "idade aumentou o risco estimado" não significa que a idade cause inadimplência.
- Os três scores externos são correlacionados; o SHAP reparte o crédito entre eles de forma que pode variar entre modelos equivalentes.
- As contribuições são calculadas em log-odds; ao titular, só a ordenação e o texto dos fatores são comunicados.
