# FINAL EVIDENCE REGISTER — Challenge 001 (RavenStack churn)

> **Nota de empacotamento (FINAL-SUBMISSION-PACKAGE-01).** Este documento foi copiado do workspace de desenvolvimento sem alterar evidência. Os scripts citados estão em `solution/scripts/` e os outputs em `solution/outputs/`. Documentos de ciclos de desenvolvimento citados como fonte (ANALYSIS-08 a 16, AUDIT-01, docs numerados 09–21, `solution/outputs/environment_rerun/`) ficaram no workspace e não fazem parte do pacote; o que eles sustentam está consolidado aqui, no apêndice técnico e nos outputs incluídos.

> **STATUS: FINAL ANALYTICAL SOURCE OF TRUTH**
>
> Data: 2026-10-04 · Consolida ANALYSIS-08 a 15, INDEPENDENT AUDIT-01 e a reexecução em ambiente liberado.
>
> **Supersedes:**
>
> - a interpretação da ANALYSIS-09 onde for inconsistente com este registro;
> - a interpretação da ANALYSIS-10 onde for inconsistente;
> - a interpretação da ANALYSIS-11 onde for inconsistente;
> - a interpretação da ANALYSIS-11B onde for inconsistente;
> - a interpretação temporal da ANALYSIS-12;
> - a interpretação temporal e de causa raiz da ANALYSIS-13.
>
> **Não apaga nenhuma análise histórica.** Os docs, scripts e outputs 08–15 permanecem intactos como trilha metodológica. Em caso de conflito, este registro prevalece.

## Hierarquia de evidência

RAW DATA > outputs reproduzíveis da ANALYSIS-15 e da AUDIT-01 > scripts validados > **FINAL-EVIDENCE-REGISTER** > relatório executivo > slides.

## Índice

| ID | Pergunta | Finding final | Confiança | Status de auditoria |
|---|---|---|---|---|
| F-01 | Qual é a taxa de churn? | Três definições incompatíveis: 22,0% / 62,4% / 70,4% | Alta | CONFIRMED |
| F-02 | O churn acelerou em Q4/2024? | Nenhum excesso acima do null calibrado | Alta | CONFIRMED (corrige ANALYSIS-13) |
| F-03 | Alguma conta saiu por inteiro? | Estado contratual observável: 0 contas terminam sem subscription ativa | Alta | CONFIRMED (corrige ANALYSIS-10/11/12) |
| F-04 | O evento de churn corresponde ao contrato? | Vínculo não maior que o acaso | Alta | CONFIRMED (corrige ANALYSIS-11/13) |
| F-05 | Os ends são upgrades, downgrades ou trocas? | Proximidade entre end e novo start não maior que o acaso | Alta | CONFIRMED (corrige ANALYSIS-11/12) |
| F-06 | Product explica churn? | Nenhum driver de Product recuperável | Alta | CONFIRMED WITH RESERVATION (razão atualizada) |
| F-07 | Support explica churn? | Nenhum driver de Support recuperável | Alta | CONFIRMED |
| F-08 | Fatores econômicos ou contratuais explicam o end? | Nenhum driver econômico ou contratual; P(end) aproximadamente constante | Alta | CONFIRMED WITH RESERVATION (linguagem) |
| F-09 | Um modelo consegue prever churn? | Nenhum sinal preditivo | Alta | CONFIRMED |
| F-10 | Fatores combinados explicam o end? | Resultado multivariável nulo | Alta | CONFIRMED |
| F-11 | O CSAT diz algo sobre churn? | Heterogêneo entre meses, sem relação com churn | Alta | CONFIRMED |
| F-12 | A qualidade do produto mudou em Q4? | Erros ~8% menores em Q4/2024; evidência fraca, sem relação com churn | Baixa | DESCRIPTIVE |
| F-13 | O claim de Product "o uso cresceu" se sustenta? | Não: NOT SUPPORTED sob os denominadores naturais | Alta | CONFIRMED |
| F-14 | Por que CEO, Product e CS discordam? | Explicação estabelecida pelos dados observados | Alta | CONFIRMED (sem dependência de lifecycle) |
| F-15 | Qual é a causa raiz do churn? | Nenhum driver recuperável nas cinco tabelas | Alta | NOT IDENTIFIABLE FROM OBSERVED DATA |
| F-16 | Onde CS/RevOps deve olhar primeiro? | Manual-renewal exposure: V3 = 388 contas · 764 registros · 2.023.778 de MRR proxy (409 / 899 só com trials de MRR zero incluídos) | Média | CORRECTED / CLARIFIED |
| F-17 | Os resultados dependem do ambiente bloqueado? | Reexecução completa confirmada | Alta | CONFIRMED |
| F-18 | Uso e suporte estão alinhados no tempo ao lifecycle? | Não: 22,27% do uso dentro da vida da assinatura; 52,8% do uso e 53,9% dos tickets antes do signup | Alta | CONFIRMED (auditor independente, reproduzido) |
| F-19 | Suporte separa contas flagged sem os tickets inválidos? | Não; continua sem separação | Alta | CONFIRMED (sensibilidade) |
| F-20 | O reason_code é coerente com o feedback textual? | Nenhuma associação detectável (p = 0,955; n = 452) | Alta | CONFIRMED (p do auditor difere; ver ficha) |
| F-21 | Registro de assinatura = contrato? `subscriptions.churn_flag` é outro alvo? | Não estabelecido; churn_flag da assinatura = ter end_date | Alta | CONFIRMED |
| F-22 | Qual é o denominador do "uso por conta ativa"? | Regra exata documentada a partir do código | Alta | DEFINITION |

> **Adendo FINAL-AUDIT-INTEGRATION-01 (2026-10-04).** F-18 a F-22 vêm de um auditor independente em chat limpo e só entraram depois de recalculados dos CSVs brutos por `solution/scripts/auditor_integration.py` (52/53 valores reproduzidos; 1 conflito de definição de teste, documentado em F-20). F-16 foi corrigido em seguida, com errata aprovada (moeda removida; 409/899 × 388/764 distinguidos).

## Fichas dos findings

### F-01 — Definições de churn

| Campo | Conteúdo |
|---|---|
| Question | Qual é a taxa de churn da RavenStack? |
| Final finding | Três definições incompatíveis coexistem: `accounts.churn_flag` 110/500 = 22,0%; contas com alguma subscription encerrada 312/500 = 62,4%; contas com churn event 352/500 = 70,4%. Elas não são versões da mesma medida: `churn_flag` não se associa nem ao número de eventos da própria conta. |
| Evidence | MWU `churn_flag` × n_events p=0,98; 35 contas com flag e sem evento; 277 com evento e sem flag. `independent_audit/account_outcome_definitions.csv`. |
| Confidence | Alta |
| Evidence class | Fato descritivo + teste de coerência |
| Source | ANALYSIS-08/10; AUDIT-01 §4 |
| Audit status | CONFIRMED |
| Executive wording | "There is no single churn number: the three internal definitions disagree and are not related to one another." |
| Forbidden wording | "O churn da RavenStack é X%" sem nomear a definição; tratar as três taxas como a mesma medida. |

### F-02 — Q4 / aumento do churn

| Campo | Conteúdo |
|---|---|
| Question | O churn acelerou em Q4/2024? |
| Final finding | Observed late-period increases in churn events and subscription ends are compatible with the recovered temporal data mechanism and do not represent excess churn above the calibrated null. **Classificação: NO EVIDENCE OF Q4 EXCESS ABOVE CALIBRATED NULL.** |
| Evidence | **AUDIT-01, 1.000 simulações do mecanismo sem driver:**<br>• IRR ajustado observado de 1,288; média do null 1,233 (IC95 0,974–1,526); percentil 67. O modelo antigo sai "significativo e positivo" em 43,2% dos datasets nulos.<br>• Ends em Q4: 324 observados; null 330,5 (296–365).<br>• Ends em dezembro: 193 observados; null 198,7 (172–225).<br>• Ends em 31/12: 24 observados; null 10–26.<br>**ANALYSIS-15, mês a mês:**<br>• Churn events em Q4/2024: 251 observados contra 251,9 esperados pelo mecanismo (p=0,99).<br>• Ajuste mensal nos 24 meses: p=0,80.<br>• Ends observados menos o esperado pelo mecanismo: mudança em Q4 de −1,28 (HAC p=0,73).<br>**Finding de apoio:** THE OBSERVED CHURN-EVENT CALENDAR DISTRIBUTION IS CONSISTENT WITH THE RECOVERED TEMPORAL MECHANISM. |
| Confidence | Alta |
| Evidence class | Null calibrado por simulação + ajuste analítico do mecanismo |
| Source | AUDIT-01 §9 (`q4_null_calibration.csv`, `expected_ends_under_generator.csv`); ANALYSIS-15 (`row_level_verification.csv`, `churn_events_vs_mechanism_monthly.csv`) |
| Audit status | CONFIRMED. Supera o finding "Q4 real late-period association" da ANALYSIS-13 |
| Executive wording | "The late-2024 rise is what the data's date structure produces on its own; there is no excess churn to explain." |
| Forbidden wording | "Q4 real late-period association"; "Q4 customer deterioration"; "subscription churn accelerated"; "boundary anomaly"; "provamos que o gerador criou isso" (o código do gerador não está disponível). |

### F-03 — Estado contratual observável da conta

| Campo | Conteúdo |
|---|---|
| Question | Alguma conta deixou de ter contrato? |
| Final finding | OBSERVABLE CONTRACT-STATE OUTCOME IS COMPUTABLE. Das 500 contas, 0 terminam 2024 com zero subscriptions ativas. 8 tiveram pelo menos um período temporário sem nenhuma ativa (3 a 72 dias) e todas voltaram a ter. Toda conta termina com pelo menos 2 registros de subscription ativos (mediana 9). |
| Evidence | Timeline diária de subscriptions ativas por conta. `independent_audit/account_activity_timeline_summary.csv`, `account_outcome_definitions.csv`. |
| Confidence | Alta para o cálculo; média para a equivalência entre o registro e o contrato real |
| Evidence class | Fato descritivo derivado dos dados |
| Source | AUDIT-01 §4–5 |
| Audit status | CONFIRMED. Supera "FULL_ACCOUNT_CHURN = UNANSWERABLE/indisponível" (ANALYSIS-10/11/12) |
| Executive wording | "Under the observable contract-state definition, no account ends the observation period with zero active subscription records." |
| Forbidden wording | "RavenStack had zero real customer churn"; "a RavenStack não perdeu nenhum cliente". Registros de subscription não equivalem à verdade comercial. |

### F-04 — Evento de churn × contrato

| Campo | Conteúdo |
|---|---|
| Question | O churn event corresponde a um encerramento de contrato? |
| Final finding | NO EVIDENCE OF EVENT-CONTRACT LINKAGE ABOVE CHANCE. Observado: 26 de 329 `VALID_CHURN_TRANSITION` têm um end de subscription a ±7 dias. Sob o null temporal, o esperado é 25,2 (IC95 17–35; percentil 56). Além disso, em 91% dos eventos a conta ainda tem subscriptions ativas (mediana 4). |
| Evidence | `independent_audit/lifecycle_links_vs_chance.csv`; `end_to_end_sweep/event_timing_checks.csv` |
| Confidence | Alta |
| Evidence class | Comparação com null simulado |
| Source | AUDIT-01 §11/13; ANALYSIS-14 §7 |
| Audit status | CONFIRMED. Supera "churn_event fracamente ligado ao contrato" (ANALYSIS-11/13) |
| Executive wording | "The observed linkage is approximately what would be expected by chance under the recovered temporal structure." |
| Forbidden wording | "weakly linked"; "fracamente ligado"; usar os 26 casos como evidência positiva de vínculo. |

### F-05 — Classificação de lifecycle

| Campo | Conteúdo |
|---|---|
| Question | Os encerramentos são upgrades, downgrades, trocas ou perdas reais? |
| Final finding | NO LIFECYCLE EXCESS ABOVE CHANCE. Proximity between subscription ends and subsequent starts does not provide reliable evidence of upgrade, downgrade, replacement or true loss. Observado: 23,0% "movement-like". Null: 24,4% (20,7–28,1%). |
| Evidence | `independent_audit/lifecycle_links_vs_chance.csv` (200 simulações) |
| Confidence | Alta |
| Evidence class | Comparação com null simulado |
| Source | AUDIT-01 §13 (AUD-16) |
| Audit status | CONFIRMED. Os rótulos 50 POSSIBLE_UPGRADE / 46 POSSIBLE_DOWNGRADE / 16 POSSIBLE_REPLACEMENT / 2 POSSIBLE_TRUE_END ficam **apenas como tentativa histórica** (ANALYSIS-11/12) |
| Executive wording | "Lifecycle type cannot be inferred from the data." |
| Forbidden wording | Citar as contagens de upgrade/downgrade/replacement/true end como achado; "112 movimentos de lifecycle". |

### F-06 — Product

| Campo | Conteúdo |
|---|---|
| Question | Uso, adoção ou erros de produto explicam churn? |
| Final finding | NO RECOVERABLE PRODUCT DRIVER. Duas camadas: **(A)** a telemetria anterior ao evento é esparsa (82,6% dos casos sem telemetria em T-30); **(B)** mesmo com todo o histórico, testes de poder alto, as 40 features abertas, uso, erros e modelos não lineares, nada fica acima do acaso. |
| Evidence | • Grão subscription com todo o histórico (486 × 4.514; menor efeito detectável d=0,13): 7 métricas, todas p>0,05.<br>• 40 features, Fisher: menor q=0,51.<br>• Random forest e gradient boosting com 80 colunas de uso e erro: AUC de 0,449 a 0,515, nenhum acima do null.<br>• Uso válido dentro da vida da subscription: 5.568 linhas, igual às 5.517,6 esperadas se as datas fossem independentes.<br>**Limitação preservada:** NO_TELEMETRY ≠ ZERO_USAGE (33 subscriptions sem telemetria; 0 com uso zero). |
| Confidence | Alta |
| Evidence class | Teste de falsificação com poder alto + modelos |
| Source | ANALYSIS-09/11B; AUDIT-01 §6; ANALYSIS-14 §5; ANALYSIS-15 §2.1 |
| Audit status | CONFIRMED WITH RESERVATION. O nulo se mantém, mas a razão "só por falta de telemetria" (evidência grau D) foi superada |
| Executive wording | "Even with full history and every feature, product behavior does not distinguish customers who leave from those who stay." |
| Forbidden wording | "telemetry sparse, therefore inconclusive" como única razão; tratar ausência de linha como uso zero; "product adoption deteriorated causes churn". |
| Method notes | **MEDIUM, sem impacto nos resultados:** (1) `fillna(0)` em `feature_usage_churn_analysis.py::add_trends` (linhas 283–284) mistura NO_TELEMETRY com uso zero; (2) a logística BFGS escrita à mão (linhas 470–494) não checava convergência e tinha um `except` que poderia gerar NaN. Os 40 ajustes foram refeitos com `statsmodels Logit`: todos convergiram, com diferença máxima de coeficiente de 4,5×10⁻⁶. Conclusões inalteradas. Pipelines futuros devem checar convergência explicitamente. Os números da ANALYSIS-09 não foram alterados retroativamente. |

### F-07 — Support

| Campo | Conteúdo |
|---|---|
| Question | Volume, tempo, escalação ou CSAT de suporte explicam churn? |
| Final finding | NO RECOVERABLE SUPPORT DRIVER. As métricas de suporte também não são coerentes entre si: prioridade não explica resolução; escalação não explica resolução; CSAT não reage a first response nem a resolução; CSAT não acompanha churn. |
| Evidence | • Grão de conta: tickets, resolução, FRT, escalações, CSAT, CSAT ausente e % urgente × `churn_flag` e × evento, todos p>0,05.<br>• Coerência interna: prioridade → resolução p=0,33; prioridade → FRT p=0,13; escalação → resolução p=0,53; CSAT ~ resolução p=0,70; CSAT ~ FRT p=0,32.<br>• CSAT ausente não é informativo (p=0,53 / 0,69).<br>• GEE: tickets p=0,69, escalações p=0,61. |
| Confidence | Alta |
| Evidence class | Testes univariados + coerência + multivariável |
| Source | ANALYSIS-10; AUDIT-01 §7; ANALYSIS-14 §6; ANALYSIS-15 §2.2 |
| Audit status | CONFIRMED |
| Executive wording | "Support metrics neither predict churn nor respond to each other, so they cannot currently measure service quality." |
| Forbidden wording | "Support caused churn"; "o suporte está saudável" com base nesses KPIs. |

### F-08 — Fatores econômicos e contratuais

| Campo | Conteúdo |
|---|---|
| Question | MRR, seats, plano, billing, trial, auto-renew ou flags explicam o end? |
| Final finding | NO RECOVERABLE ECONOMIC OR CONTRACT DRIVER. P(end) is approximately constant across observed attributes. Nuance: as coortes pequenas de 2023 têm P(end) um pouco maior (χ² p=0,018; no GEE, semestre de início p≈0,010, q≈0,22), o que não é robusto após correção por múltiplos testes. **NO ROBUST COHORT DRIVER.** |
| Evidence | • P(end) por plano 9,5–10,0% (p=0,89); billing p=0,49; trial p=0,80; auto-renew p=0,98; upgrade p=0,45; downgrade p=0,44.<br>• MRR = seats × preço fixo por plano (19/49/199).<br>• Cox da ANALYSIS-12: q≥0,10 para MRR, seats, trial, plano e billing.<br>• GEE: log MRR p=0,47; plano p=0,92.<br>• O único segmento que passou no FDR na ANALYSIS-14 (indústria × alguma sub encerrada, q=0,031) não replica na taxa por subscription (p=0,36 cluster-robust; 0,64 por permutação). |
| Confidence | Alta |
| Evidence class | Testes por atributo + Cox + GEE |
| Source | ANALYSIS-12; AUDIT-01 §8; ANALYSIS-14 §4/§9; ANALYSIS-15 §2.2 |
| Audit status | CONFIRMED WITH RESERVATION. "P(end) constante" foi corrigido para "aproximadamente constante" |
| Executive wording | "Price, plan, contract terms and account size do not explain which subscriptions end." |
| Forbidden wording | "Price caused churn"; "P(end) é constante"; "later cohorts terminate faster" como achado de negócio. |

### F-09 — Modelos preditivos

| Campo | Conteúdo |
|---|---|
| Question | Algum modelo separa churn de não churn? |
| Final finding | ADVANCED MODELS DO NOT RECOVER A CHURN SIGNAL. **NO PREDICTIVE SIGNAL.** |
| Evidence | **ANALYSIS-15**, 100–106 variáveis com as 40 features abertas, média de 5 sementes de validação, cada modelo contra o próprio null (50 permutações):<br>• Subscription end: random forest AUC 0,503 (p=0,39); gradient boosting AUC 0,515 (p=0,22).<br>• `churn_flag`: random forest 0,490 (p=0,61); gradient boosting 0,449 (p=0,80).<br>• Churn event: random forest 0,458 (p=0,86); gradient boosting 0,482 (p=0,94).<br>**ANALYSIS-14**: 9 modelos (logística, árvore e gradient boosting × 3 outcomes) com AUC fora da amostra de 0,454 a 0,538 (reproduzido idêntico em FINAL-AUDIT-INTEGRATION-01), nenhum acima do próprio null. |
| Confidence | Alta |
| Evidence class | Validação cruzada + null por permutação |
| Source | ANALYSIS-14 §9; ANALYSIS-15 §2.1 |
| Audit status | CONFIRMED |
| Executive wording | "Mesmo modelos não lineares capazes de capturar interações entre mais de 100 variáveis não conseguem separar churn de não churn melhor que o acaso." |
| Forbidden wording | "um modelo mais avançado encontraria o sinal"; apresentar qualquer score como preditivo. |

### F-10 — GEE multivariável

| Campo | Conteúdo |
|---|---|
| Question | Os antecedentes, juntos e com cluster por conta, explicam o end? |
| Final finding | MULTIVARIABLE RESULT REMAINS NULL. 21 fatores modelados ao mesmo tempo, com cluster por conta; nenhum q<0,10; correlação de trabalho ≈ −0,007. Subscriptions belonging to the same observed account do not show material within-account outcome correlation in this dataset. |
| Evidence | `unblocked_models/gee_subscription_end.csv`: menor p=0,010 (semestre de início, q=0,22). Todos os demais p≥0,16. |
| Confidence | Alta |
| Evidence class | Modelo multivariável com cluster por conta |
| Source | ANALYSIS-15 §2.2 |
| Audit status | CONFIRMED |
| Executive wording | "Estimated within-account correlation is effectively zero, and no antecedent matters once all are considered together." |
| Forbidden wording | "subscriptions são absolutamente independentes". |

### F-11 — CSAT

| Campo | Conteúdo |
|---|---|
| Question | O CSAT informa sobre churn ou sobre a experiência do cliente? |
| Final finding | CSAT has real month-to-month heterogeneity but no persistent, seasonal or churn-related pattern. |
| Evidence | • Médias mensais de 3,73 a 4,36; heterogeneidade mensal p≈0,005 (permutação).<br>• Sazonalidade: ρ≈0,21, p≈0,51.<br>• × churn no mesmo mês: ρ≈−0,23, p≈0,28.<br>• × churn no mês seguinte: ρ≈0,21, p≈0,33.<br>• × ends de subscription: ρ≈−0,25, p≈0,23.<br>• × tickets: ρ≈−0,26, p≈0,22.<br>• × taxa de erro: ρ≈0,17, p≈0,44.<br>• Autocorrelação mensal de −0,11.<br>• 41,25% sem resposta; escala observada só 3–5. |
| Confidence | Alta |
| Evidence class | Testes no nível da resposta + séries |
| Source | ANALYSIS-10; AUDIT-01 §7; ANALYSIS-15 §2.3 (`row_level_verification.csv`) |
| Audit status | CONFIRMED. A redação "CSAT é plano" foi superada |
| Executive wording | "CSAT varies, but the variation carries no recoverable information about churn or operational service quality." |
| Forbidden wording | "CSAT é plano"; "healthy CSAT" ou "satisfação saudável" como evidência de boa experiência. |

### F-12 — Taxa de erro de produto em Q4/2024

| Campo | Conteúdo |
|---|---|
| Question | A qualidade técnica do produto mudou no fim do período? |
| Final finding | Product error rate was approximately 8% lower in Q4/2024. **DESCRIPTIVE · WEAK EVIDENCE · NOT CHURN RELATED.** |
| Evidence | Erros por linha de uso: 0,525 em Q4/2024 contra 0,570 nos demais trimestres. Permutação com correção de "procurar em todos os trimestres": p≈0,026. Não sobrevive à família mais ampla de 9 séries. A direção é oposta a "mais erros → mais churn". |
| Confidence | Baixa |
| Evidence class | Observação descritiva secundária |
| Source | ANALYSIS-15 §2.3 |
| Audit status | DESCRIPTIVE |
| Executive wording | "A small, weakly supported dip in product errors in Q4/2024 has no relationship with churn." |
| Forbidden wording | Qualquer recomendação causal a partir deste dado; "melhoria de qualidade reduziu churn". |

### F-13 — Claim de Product "usage grew": NOT SUPPORTED (denominador)

| Campo | Conteúdo |
|---|---|
| Question | O uso da plataforma cresceu? |
| Final finding | Product's statement that usage grew is not supported by the raw aggregate data under the most natural denominators. |
| Evidence | Tabela oficial abaixo. No nível da linha, Q4/2024 tem 3.204 linhas de uso contra 3.146 esperadas sob distribuição uniforme (p=0,31). |
| Confidence | Alta |
| Evidence class | Agregados brutos com denominador explícito |
| Source | AUDIT-01 §16; ANALYSIS-14 §3; ANALYSIS-15 §2.3 |
| Audit status | CONFIRMED |
| Executive wording | "Total usage is flat while the customer base grew, so usage per customer fell sharply." |
| Forbidden wording | "product adoption deteriorated causes churn"; usar volume acumulado como prova de crescimento. |

| Trimestre | Uso total | Uso por conta ativa | Uso por subscription ativa |
|---|---|---|---|
| 2023Q1 | 31.400 | 1.495,2 | 1.012,9 |
| 2023Q2 | 31.128 | 438,4 | 230,6 |
| 2023Q3 | 31.155 | 237,8 | 92,7 |
| 2023Q4 | 30.878 | 162,5 | 47,7 |
| 2024Q1 | 31.593 | 121,5 | 28,9 |
| 2024Q2 | 30.789 | 91,4 | 17,7 |
| 2024Q3 | 31.355 | 75,6 | 11,3 |
| 2024Q4 | 32.227 | 64,5 | 7,1 |
| **Classificação** | **FLAT** (≈31 mil por trimestre; índice 100 → 103) | **DECREASING** (−96%) | **DECREASING** (−99%) |

### F-14 — Contradição CEO × Product × CS

| Campo | Conteúdo |
|---|---|
| Question | Por que os três times veem realidades diferentes? |
| Final finding | **EXPLANATION ESTABLISHED FROM OBSERVED DATA.** A contradição nasce de seis fatores:<br>(1) métricas com grãos diferentes;<br>(2) numeradores sem os denominadores adequados;<br>(3) eventos gerados de forma independente e desacoplados no tempo;<br>(4) CSAT com escala truncada e não resposta;<br>(5) vínculo entre churn event e subscription end não maior que o acaso;<br>(6) volume bruto de uso lido sem normalizar pela população em crescimento.<br>A explicação não depende mais de "lifecycle movements". |
| Evidence | Ver os claims separados abaixo e F-01, F-04, F-11 e F-13. |
| Confidence | Alta |
| Evidence class | Síntese de findings confirmados |
| Source | AUDIT-01 §16; ANALYSIS-14 §3; ANALYSIS-15 |
| Audit status | CONFIRMED |
| Executive wording | "Each team is reading a real number through a different lens; none of the three numbers measures customer health." |
| Forbidden wording | "lifecycle misturado" como causa da contradição; "dados ruins causam churn". |

**Os três claims, separados:**

| Claim | Camada | Status |
|---|---|---|
| CEO: "churn cresceu" | OBSERVED COUNT: os churn events sobem (6 em 2023Q1 → 251 em 2024Q4) | Fato descritivo |
| | OBSERVED RATE PER ACCOUNT: eventos por 100 contas sobem de 10,9 para 50,2 | Fato descritivo |
| | BUSINESS INTERPRETATION: "a deterioração dos clientes aumentou" | **NOT SUPPORTED.** A distribuição observada dos eventos é reproduzida pelo mecanismo temporal recuperado (F-02) |
| Product: "o uso cresceu" | Agregados brutos sob os denominadores naturais | **NOT SUPPORTED BY RAW AGGREGATES** (F-13) |
| CS: "a satisfação está ok" | CSAT estável na tendência, truncado (3–5), 41,25% sem resposta, desconectado da operação | **AMBIGUOUS.** O número não mede a experiência (F-11) |

### F-15 — Causa raiz do customer churn

| Campo | Conteúdo |
|---|---|
| Question | O que está causando o churn? |
| Final finding | **NO RECOVERABLE DRIVER OF CUSTOMER CHURN WAS FOUND IN THE FIVE OBSERVED TABLES.** The observed outcomes are statistically compatible with a temporal data-generation mechanism that does not depend on Product, Support, Revenue, contract, segment or acquisition antecedents.<br>**Status: NOT IDENTIFIABLE FROM OBSERVED DATA + ZERO-DRIVER MECHANISM CONSISTENT WITH DATA.** |
| Evidence | F-02 a F-10 juntos:<br>• 89 testes de falsificação com 0 p<0,05 (AUDIT-01);<br>• 39 testes de segmento sem driver robusto (ANALYSIS-14);<br>• 15 modelos preditivos sem sinal acima do null (ANALYSIS-14/15);<br>• GEE com 21 termos e 0 q<0,10;<br>• reason codes sem coerência com nenhum antecedente (support × tickets p=0,82; features × erros p=0,98; pricing × MRR p=0,68). |
| Confidence | Alta |
| Evidence class | Convergência de testes univariados, multivariáveis, preditivos e nulls calibrados |
| Source | AUDIT-01 §15; ANALYSIS-14; ANALYSIS-15 |
| Audit status | NOT IDENTIFIABLE FROM OBSERVED DATA |
| Executive wording | "We found no recoverable behavioral, support, economic or segment driver of cancellation in the observed five-table dataset. The outcomes are consistent with a temporal generation mechanism that does not depend on those antecedents." |
| Forbidden wording | "provamos que nenhuma causa existe"; "o gerador definitivamente não tem causa"; "dados ruins causam churn"; "Product caused churn"; "Support caused churn"; "Price caused churn". |

### F-16 — Manual-renewal exposure / Contractual review universe

**STATUS: CORRECTED / CLARIFIED** (errata aprovada por Samuel em 2026-10-04; números recalculados dos CSVs brutos antes de gravar)

| Campo | Conteúdo |
|---|---|
| Question | Existe algum recorte operacional legítimo para CS/RevOps? |
| Final finding | Há **409 contas** com pelo menos um registro ativo `auto_renew_flag=false`, totalizando **899 registros**. Esse universo inclui exposições sem valor econômico: **21 das 409 contas** possuem somente exposições `auto_renew=false` de trial com MRR proxy zero; essas contas podem possuir outras assinaturas pagas ativas (nos dados, todas as 21 possuem); portanto, não pertencem à população econômica V3.<br>**População operacional V3:** **388 contas**; **764 registros** ativos `auto_renew=false` com MRR proxy > 0; **2.023.778 de MRR proxy**; **19,9%** do MRR proxy ativo.<br>Os 899 registros = 764 com MRR proxy > 0 + 135 registros de trial com MRR proxy zero (em 111 contas, das quais 21 só têm esse tipo de exposição). |
| Uso correto de cada número | **409 / 899:** "qualquer registro ativo `auto_renew=false`, incluindo trials com MRR zero". **388 / 764:** "manual-renewal exposure with positive MRR proxy". |
| Currency | O dataset não estabelece moeda para `mrr_amount`. Não atribuir símbolo ou código monetário. |
| Interpretation | População operacional para revisão de renovação, **não** uma estimativa de churn ou de receita perdida. |
| Evidence | Registros ativos em 31/12/2024. Não existe `renewal_due_date`. Recalculado em `solution/scripts/final_rewrite_build.py` (`final_numbers.json`: V3) e `solution/scripts/auditor_integration.py` (`auditor_integration_summary.json`: V3_21_accounts). |
| Confidence | Média (MRR é proxy por registro; sem data de renovação) |
| Evidence class | Fato contratual descritivo |
| Source | AUDIT-01 §17; SOLUTION-VALIDATION-02; FINAL-REWRITE-01; FINAL-AUDIT-INTEGRATION-01 |
| Audit status | CORRECTED / CLARIFIED — recorte operacional |
| Executive wording | Permitido: "manual-renewal exposure"; "contractual review universe"; "MRR proxy"; "business-priority population". "Population that RevOps/CS can audit first after renewal timing is properly instrumented." |
| Forbidden wording | "Revenue at Risk"; "predicted churn risk"; "expected loss"; "expected savings"; "revenue"; R$ / BRL / USD; "CHURN WATCHLIST"; "HIGH-RISK CUSTOMERS"; "LIKELY TO CHURN"; "they will expire". |

<details>
<summary>Redação anterior (SUPERSEDED em 2026-10-04 — mantida só como histórico; não usar)</summary>

> **CONTRACTUAL EXPOSURE REVIEW UNIVERSE:** 899 registros de subscription ativos com `auto_renew_flag=false`, em 409 contas, somando R$ 2,02 mi de MRR proxy por registro (≈19,9% do MRR proxy ativo). 456 desses registros são mensais (R$ 1,02 mi). As 20 maiores contas concentram 22,8% do valor. É uma população para auditar, não uma previsão.
>
> Motivos da correção: moeda atribuída sem base no dataset; 409 contas usadas como população econômica, quando 21 delas só têm exposição de trial com MRR zero.

</details>

### F-17 — Reexecução completa do ambiente

| Campo | Conteúdo |
|---|---|
| Question | Os resultados foram afetados pelo bloqueio do Smart App Control? |
| Final finding | **FULL ENVIRONMENT RERUN CONFIRMED.** O bloqueio do ambiente não explica os resultados nulos nem as conclusões do projeto. |
| Evidence | • 7 pipelines reexecutados (09, 10, 11, 11B, 12, 13, AUDIT-01 com 1.000 simulações), com outputs comparados célula por célula.<br>• Nenhum resultado material mudou. As únicas diferenças numéricas estão na 16ª casa decimal; as de texto são células vazias dos dois lados.<br>• Nenhum dos 179 arquivos originais foi alterado (manifesto MD5).<br>• As análises antes impossíveis (ensembles, séries temporais, GEE) foram executadas e mantêm o veredito.<br>Evidência em `solution/outputs/environment_rerun/`. |
| Confidence | Alta |
| Evidence class | Reprodutibilidade |
| Source | ANALYSIS-15 §1 |
| Audit status | CONFIRMED |
| Executive wording | "O bloqueio do ambiente não explica os resultados nulos nem as conclusões do projeto." |
| Forbidden wording | "os nulos podem ser efeito do ambiente"; "não testamos modelos suficientemente avançados". |

### F-18 — Qualidade temporal de uso e suporte

| Campo | Conteúdo |
|---|---|
| Question | Uso e tickets estão alinhados no tempo ao lifecycle da conta e da assinatura? |
| Final finding | **NÃO.** Só 5.568 / 25.000 linhas de uso (22,27%) caem dentro da vida observada da assinatura vinculada. 13.198 / 25.000 (52,8%) são anteriores ao signup da conta. 1.077 / 2.000 tickets (53,9%) são anteriores ao signup. |
| Evidence | `solution/scripts/auditor_integration.py` → `solution/outputs/auditor_integration/temporal_data_quality.csv`. |
| Confidence | Alta |
| Evidence class | Contagem direta nos CSVs brutos |
| Source | Auditor independente em chat limpo; reproduzido em FINAL-AUDIT-INTEGRATION-01 |
| Audit status | CONFIRMED |
| Executive wording | "Data quality also blocks behavioral interpretation: 52.8% of usage rows and 53.9% of support tickets predate account signup." |
| Forbidden wording | "dataset quebrado"; "erro do gerador"; usar a inconsistência como causa de churn. |

### F-19 — Sensibilidade de suporte sem tickets anteriores ao signup

| Campo | Conteúdo |
|---|---|
| Question | Suporte passa a separar contas flagged quando os tickets temporalmente inválidos são removidos? |
| Final finding | **NÃO.** Com 923 tickets válidos, médias por conta (flagged × demais): tickets 2,43 × 2,48; first response 88,8 × 89,8 min; resolução 34,4 × 35,8 h; escalação 7,0% × 5,5%; CSAT 4,03 × 3,94. Mann-Whitney p de 0,31 a 0,95. |
| Evidence | `solution/outputs/auditor_integration/support_post_signup_sensitivity.csv`. |
| Confidence | Alta |
| Evidence class | Análise de sensibilidade |
| Source | Auditor independente; reproduzido |
| Audit status | CONFIRMED (reforça F-07) |
| Executive wording | "Support remains non-separating even after correcting the obvious temporal inconsistency." |
| Forbidden wording | "escalação prevê churn" (7,0% × 5,5%, p = 0,86). |

### F-20 — reason_code × feedback textual

| Campo | Conteúdo |
|---|---|
| Question | O motivo codificado de saída é coerente com o feedback textual? |
| Final finding | **Nenhuma associação detectável.** 452 de 600 churn events têm feedback; só há 3 textos distintos. χ² nos 452: p = 0,955 (permutação 0,958; V de Cramér 0,065). Dos 136 "switched to competitor", só 21 têm `reason_code = competitor`. |
| Evidence | `solution/outputs/auditor_integration/reason_feedback_alignment.csv`; `auditor_integration_summary.json`. |
| Confidence | Alta |
| Evidence class | Teste de independência |
| Source | Auditor independente; reproduzido com divergência de definição |
| Audit status | CONFIRMED. **Conflito registrado:** o auditor reportou p ≈ 0,986, que reproduz só com os 148 feedbacks vazios como categoria (n = 600). Valor adotado: 0,955 (n = 452). A conclusão não muda. |
| Executive wording | "Nem a variável destinada a registrar por que o cliente saiu apresenta coerência detectável com o feedback textual registrado." |
| Forbidden wording | "reason_code está errado em 100% dos casos". |

### F-21 — Semântica das assinaturas

| Campo | Conteúdo |
|---|---|
| Question | Cada registro de assinatura equivale a um contrato? `subscriptions.churn_flag` é uma definição independente de churn? |
| Final finding | **Não estabelecido.** No fim da observação: 4.514 registros ativos, 9,0 por conta; 418 / 500 contas com Basic, Pro e Enterprise ativos ao mesmo tempo; 496 / 500 com ≥ 2 planos. `subscriptions.churn_flag = true` em 486 registros, exatamente os 486 com `end_date`; nenhum false tem end_date. |
| Evidence | `solution/outputs/auditor_integration/subscription_semantics.csv`. |
| Confidence | Alta |
| Evidence class | Contagem direta |
| Source | Auditor independente; reproduzido |
| Audit status | CONFIRMED (reforça F-03 e F-05) |
| Executive wording | "The schema does not establish that each subscription record maps one-to-one to a commercial contract." · "At subscription grain, churn_flag is effectively a duplicate representation of subscription end." |
| Forbidden wording | "subscription is fake"; "dataset is broken"; "subscriptions do not represent contracts"; contar `subscriptions.churn_flag` como quinta definição. |

### F-22 — Denominador do uso por conta ativa

| Campo | Conteúdo |
|---|---|
| Question | Qual regra define "conta ativa" no uso por conta? |
| Final finding | **Uso por conta ativa (P)** = soma de `usage_count` com `usage_date` em P ÷ nº de contas com ≥ 1 registro de assinatura com `start_date` ≤ fim(P) e (`end_date` vazio ou > fim(P)). Mesma regra em `final_rewrite_build.py` (`act_accounts`) e `end_to_end_sweep.py` (`accounts_with_active_sub_eom`). Contas ativas: 190 em 31/12/2023 e 500 em 31/12/2024. |
| Evidence | `solution/outputs/auditor_integration/usage_denominator_definition.json`. |
| Confidence | Alta |
| Evidence class | Leitura do código + recálculo |
| Source | FINAL-AUDIT-INTEGRATION-01 |
| Audit status | DEFINITION (complementa F-13) |
| Executive wording | "Active account = account with ≥ 1 subscription record active at the period-end date." |
| Forbidden wording | Citar "uso por conta" sem o denominador. |

## Situação dos artefatos bloqueados

| Artefato | Status | Razão |
|---|---|---|
| HEALTH SCORE | NOT SUPPORTED | There is no recoverable churn signal (F-09, F-10, F-15) |
| EARLY WARNING | NOT SUPPORTED | Idem |
| PREDICTIVE CHURN MODEL | NOT SUPPORTED | Idem; RF, gradient boosting e GEE testados |
| REVENUE AT RISK | NOT SUPPORTED | Sem propensão válida e sem data de renovação; só existe exposição (F-16) |

A razão **não é** "não tentamos modelos suficientemente avançados".

## Findings SUPERSEDED (mantidos só como histórico)

| Finding superado | Origem | Substituído por |
|---|---|---|
| Q4 real late-period association (IRR 1,288, p=0,017) | ANALYSIS-13 | F-02 |
| Q4 customer deterioration / churn accelerated | ANALYSIS-12/13, CLAUDE.md anterior | F-02, F-14 |
| STRONG BOUNDARY EFFECT como anomalia | ANALYSIS-13 | F-02 |
| Later cohorts terminate faster (HR 1,175/mês) como achado de negócio | ANALYSIS-12 | F-08 |
| Incidência mensal subindo (IRR 1,170) como deterioração | ANALYSIS-12 | F-02 |
| 112 movimentos de lifecycle / contagens POSSIBLE_* | ANALYSIS-11/12/13 | F-05 |
| churn_event fracamente ligado ao contrato | ANALYSIS-11/13 | F-04 |
| FULL_ACCOUNT_CHURN indisponível / UNANSWERABLE | ANALYSIS-10/11/12 | F-03 |
| Nulo de Product explicado só por falta de telemetria (grau D) | ANALYSIS-11B/13 | F-06 |
| "Lifecycle misturado" como parte da causa da contradição | ANALYSIS-13 | F-14 |
| "P(end) é constante" | AUDIT-01 | F-08 |
| "CSAT é plano" | AUDIT-01, ANALYSIS-14 | F-11 |
| "provam que não há nenhuma causa embutida" | AUDIT-01 | F-15 |
