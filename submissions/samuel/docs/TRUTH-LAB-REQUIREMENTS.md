# Churn Truth Lab — requisitos (construído e validado)

**Status:** **construído e validado** (TRUTH-LAB-BUILD-02; ajustes finais de wording e idioma em FINAL-CLOSEOUT-TRUTH-LAB-01) em `solution/truth-lab/`. Estático e offline, abre direto no navegador, sem backend e sem rede externa, 6 telas funcionais, 213 testes automáticos aprovados. Dados gerados em Python a partir dos outputs validados; o navegador só calcula o break-even sobre o custo digitado pelo usuário. Interface em português; rótulos canônicos em inglês. Validação em `docs/TRUTH-LAB-VALIDATION.md` e `docs/TRUTH-LAB-VALIDATION.md` do workspace de desenvolvimento.

**Formato:** página HTML estática (abre no navegador, sem backend) sobre as 5 tabelas.

**Objetivo:** permitir que o CEO veja qual número de churn é real e que o CS saiba em quem agir amanhã, sem nenhuma previsão.

## Requisitos globais (obrigatórios)

| # | Requisito |
|---|---|
| G1 | **Nenhuma probabilidade de churn, score de risco ou "Revenue at Risk"** em nenhuma tela. As flags de qualidade de dados são descritivas e nunca são somadas num score. |
| G2 | **Rótulo de incerteza em todo número.** Ao passar o mouse ou num painel lateral, cada número mostra: **SOURCE** (tabela e regra), **GRAIN** (conta, registro, ticket, evento), **COVERAGE** (quantos registros ou contas entram) e **CONFIDENCE / LIMITATION**. |
| G3 | **Rótulos padrão:** "MRR proxy — not consolidated revenue" · "Scenario — not forecast" · "Business priority — not predicted churn risk" · "Observable contract state — commercial semantics not validated" · "Usage coverage = 22.27% inside subscription lifecycle" · "Observed — not validated as higher risk". |
| G4 | **Sem moeda** em valores de MRR (o dataset não declara unidade). |
| G5 | **Números idênticos aos de** `solution/outputs/final_rewrite/final_numbers.json` e `solution/outputs/auditor_integration/auditor_integration_summary.json`, com teste automático. |
| G6 | **Denominador explícito.** Todo gráfico de uso por conta mostra no tooltip: *"Active account = account with ≥ 1 subscription record active at the period-end date (start_date ≤ period end and end_date empty or after it). Numerator = all usage_count dated in the period."* (regra em `solution/outputs/auditor_integration/usage_denominator_definition.json`). |

## Abas

| Aba | Conteúdo | Rótulos obrigatórios |
|---|---|---|
| **1. Verdade do churn** | Três sinais de churn (110 / 352 / 312) + uma checagem de estado observável (0) — quatro respostas diferentes — com visual de sobreposição (75 / 72 / 227 / 50). Destaque: "as 110 contas flagged ainda possuem registros de subscription ativos com MRR proxy positivo". Abaixo, o bloco **"Por que uma previsão não é suportada hoje"** com 4 cards (ver abaixo) | Observable contract state — commercial semantics not validated |
| **2. Denominador** | Uso total × uso por conta ativa × uso por assinatura; seletor de segmento (indústria, país, plano); eventos × base | Usage coverage = 22.27% inside subscription lifecycle; tooltip G6 |
| **3. Filas de ação** | V1 (110), V2 (50) e V3-W1 (50), com a união de 176 e as sobreposições; filtros por fila; exportação da lista | Business priority — not predicted churn risk |
| **4. Brief da conta** | Ao clicar numa conta: valor (MRR proxy e faixa), registros ativos e encerrados, exposição sem auto-renew, uso (com cobertura), tickets e escalações, churn events, **flags de qualidade de dados** (ver abaixo), perguntas sugeridas para o CSM e próximo passo da fila | MRR proxy — not consolidated revenue; nenhuma probabilidade |
| **5. Simulador de impacto** | Controle de 0–20% sobre a exposição V3 (2.023.778 de MRR proxy) → MRR proxy e valor anualizado condicionais; campo opcional de custo do programa → taxa de break-even = custo ÷ exposição | Scenario — not forecast; no probability; no causal estimate |
| **6. Confiança dos dados** | Tabela de status por dimensão (ver abaixo); cobertura por tabela; campos ausentes | — |

### Aba 1 — "Por que uma previsão não é suportada hoje"

Rótulo do bloco: **DATA QUALITY / SEMANTIC ALIGNMENT** (não são causas de churn).

| Card | Valor | Detalhe |
|---|---|---|
| Usage before signup | **52,8%** | 13.198 / 25.000 linhas de uso anteriores ao signup da conta |
| Tickets before signup | **53,9%** | 1.077 / 2.000 tickets anteriores ao signup da conta |
| Usage inside subscription lifecycle | **22,27%** | 5.568 / 25.000 linhas dentro da vida observada da assinatura |
| reason_code vs feedback_text | **p = 0,955** | 452 eventos com feedback; nenhuma associação detectável |

### Aba 4 — flags de qualidade de dados por conta

Descritivas, sim/não, **sem soma, sem peso, sem ordenação por elas**. Fonte: `solution/outputs/auditor_integration/account_data_quality_flags.csv`.

| Flag | Regra | Contas com flag |
|---|---|---|
| `usage_before_signup` | ≥ 1 linha de uso anterior ao `signup_date` | 490 |
| `ticket_before_signup` | ≥ 1 ticket anterior ao `signup_date` | 389 |
| `multiple_plan_overlap` | registros ativos de ≥ 2 planos no fim da observação | 496 |
| `churn_flag_event_end_mismatch` | `churn_flag`, ter churn event e ter assinatura encerrada não concordam | 400 |
| `non_auto_renew_zero_mrr_only` | toda a exposição `auto_renew = false` ativa é trial com MRR proxy zero | 21 |

### Aba 6 — Confiança dos dados

| Dimensão | Status | Evidência |
|---|---|---|
| Outcome definition | **RED** | 110 / 352 / 312 = três populações de churn conflitantes; 0 = checagem do estado observável no fim. No reconciled customer-loss target |
| Subscription semantics | **RED** | 9,0 registros ativos por conta; 418 / 500 com os três planos ativos |
| Renewal dates | **RED** | campo inexistente |
| Contract ID | **RED** | campo inexistente |
| Product ID | **RED** | campo inexistente |
| Usage lifecycle alignment | **PARTIAL** | 22,27% |
| Usage before signup | **WARNING** | 52,8% |
| Support before signup | **WARNING** | 53,9% |
| Reason code semantic coherence | **RED** | p ≈ 0,95 contra o feedback textual |
| Histórico financeiro | **PARTIAL** | MRR proxy por registro (record-level) |
| Health score readiness | — | 0 GREEN · 2 PARTIAL · 8 RED |

Nota: `subscriptions.churn_flag` não aparece como definição própria; ele é idêntico a ter `end_date` (486 = 486).

## Critérios de aceite

- [x] Os 6 itens de conteúdo estão presentes: reconciliação de definições, detalhe por conta, filas V1/V2/V3, brief com as 5 tabelas, simulador e confiança dos dados.
- [x] Nenhuma tela mostra probabilidade, score ou "risco previsto".
- [x] Todo número tem SOURCE / GRAIN / COVERAGE / LIMITATION.
- [x] Todo gráfico de uso por conta mostra a definição do denominador.
- [x] O bloco "Por que uma previsão não é suportada hoje" está rotulado como qualidade de dados, não como causa.
- [x] Os números batem com os dois JSONs de G5.
- [x] Abre localmente, sem servidor.
