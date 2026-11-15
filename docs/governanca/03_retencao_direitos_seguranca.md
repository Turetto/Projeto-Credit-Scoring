# 3. Retenção, direitos do titular e segurança

> Documento de governança de um projeto acadêmico. Prazos e fundamentos seguem a LGPD (Lei 13.709/2018) e normas setoriais citadas, mas, em uma operação real, exigiriam validação do encarregado (DPO) e do jurídico.

## 3.1 Política de retenção (arts. 15 e 16)

| Local | Conteúdo | Prazo | Fundamento | Mecanismo |
|---|---|---|---|---|
| `data/quarantine/` | Lotes e linhas reprovados, com os valores que violaram o contrato | **30 dias** | Finalidade (corrigir a origem e reprocessar) se esgota no prazo (art. 15, I) | **Expurgo automatizado** (`governance/retention.py`) |
| `data/production/incoming/`, `accepted/` | Lotes brutos recebidos e aceitos | **90 dias** | Janela de reprocessamento; depois, `scored/` é o registro da decisão e os brutos são redundantes (art. 6º, III) | **Expurgo automatizado** |
| `data/production/scored/`, `labels/` | Features, score, decisão e rótulo | **5 anos** | Revisão de decisões (art. 20), auditoria e monitoramento; alinhado ao prazo de informações negativas do CDC (art. 43, §1º) | Procedimento manual (fora do escopo da simulação) |
| `data/reference/` | Dados de treino e teste | Vida útil do modelo + 5 anos | Reprodutibilidade e auditoria do modelo | Procedimento manual |
| `data/raw/` | Arquivo de origem (122 colunas) | Em produção: não persistir após a ingestão | Só 21 colunas são necessárias (art. 6º, III) | Mantido no projeto **apenas** para reprodutibilidade acadêmica |
| `logs/`, `mlflow.db` | Eventos e métricas agregados (sem dado pessoal, garantido por teste) | 1 ano (operacional) | Não sujeito à LGPD por não conter dado pessoal | — |
| `reports/`, `docs/` | Agregados | Indeterminado | Sem dado pessoal | — |

O expurgo roda em modo **simulação** por padrão (lista e registra) e só elimina com `--executar`, por ser irreversível. Toda execução gera um evento `retencao` no log, com contagens e sem nomes nem conteúdo, como prova de cumprimento (art. 6º, X).

## 3.2 Direitos do titular (art. 18)

| Direito | Aplicabilidade | Como é atendido |
|---|---|---|
| Confirmação e acesso (I, II) | Sim | Localização pelo identificador pseudonimizado (`SK_ID_CURR`) em `reference/` e `scored/`, incluindo o score inferido |
| Correção (III) | Sim | Correção na origem; o próximo lote reprocessado reflete o dado corrigido |
| Anonimização, bloqueio ou eliminação de dados desnecessários (IV) | Sim | Atendido por desenho: minimização na ingestão (21 de 122 colunas) e expurgo dos lotes brutos |
| Eliminação de dados tratados com consentimento (VI) | **Não diretamente**: as bases são o art. 7º, V, X e IX | Mesmo assim, ao fim da retenção os dados são eliminados (art. 16) |
| Informação sobre compartilhamento (VII) | Sim | Bureaus de crédito (scores externos), sob a Lei 12.414/2011 |
| Revisão de decisão automatizada (art. 20) | Sim | Ver documento 2, §2.6 |

**Eliminação × modelo treinado:** quando um dado é eliminado, ele deixa de compor os conjuntos de **retreino**. O modelo em produção guarda apenas parâmetros agregados, não registros individuais; remover a influência de um indivíduo de um modelo já treinado ("desaprendizado") não é viável na prática. A influência desaparece no retreino seguinte.

## 3.3 Medidas de segurança (art. 46)

| Medida | Estado | Evidência |
|---|---|---|
| Dados pessoais fora do controle de versão | **Implementada** | `.gitignore` (`data/*/*`, `models/*`) |
| Barreira contra commit acidental de dataset | **Implementada** | Hook `check-added-large-files` (1 MB) no pre-commit |
| Log sem dados pessoais | **Implementada e testada** | `test_log_nao_contem_valores_de_clientes` |
| Pseudonimização do identificador | **Implementada** | `SK_ID_CURR` é chave substituta; nunca é feature |
| Minimização (só o necessário entra no pipeline) | **Implementada** | `usecols` na ingestão; `MODEL_FEATURES` explícito; `test_governanca_modelo_nao_usa_id_rotulo_ou_genero` |
| Credenciais fora do repositório | **Implementada** | Token do Kaggle no perfil do usuário; `.env` e `kaggle.json` no `.gitignore` |
| Relatórios públicos sem identificação | **Implementada e verificada** | Evidently recebe só features + score; busca por ID nos HTML sem ocorrências; descrição individual do EDA generalizada |
| Criptografia em repouso | **Recomendada** (não aplicável ao ambiente local) | Em produção: armazenamento com criptografia gerenciada |
| Controle de acesso por papel | **Recomendada** | Em produção: acesso a `data/` restrito a papéis de dados; quarentena com acesso ainda mais restrito |

## 3.4 Resposta a incidentes (art. 48)

1. **Contenção:** isolar o local afetado e interromper o pipeline (o orquestrador para lote a lote).
2. **Avaliação:** usar o mapa de armazenamento (documento 1, §1.4) para determinar quais dados e titulares foram expostos. Logs e relatórios não contêm dado pessoal, o que limita o escopo.
3. **Comunicação:** à ANPD e aos titulares afetados, quando houver risco ou dano relevante, no prazo da regulamentação da ANPD (3 dias úteis, conforme a Resolução CD/ANPD nº 15/2024).
4. **Registro:** documentar o incidente e as medidas, mesmo que não comunicado (responsabilização).

## 3.5 Relatório de impacto (art. 38)

Decisão automatizada de crédito, com uso de dados de terceiros e possibilidade de efeito discriminatório, é tratamento de alto risco. A elaboração de um **Relatório de Impacto à Proteção de Dados (RIPD)** é recomendada. Os documentos 1 a 5 desta pasta cobrem os elementos centrais de um RIPD: descrição dos dados, finalidades, bases legais, medidas de segurança, análise de risco discriminatório e mitigação.
