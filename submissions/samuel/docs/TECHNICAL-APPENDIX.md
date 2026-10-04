# Apêndice técnico — evidência por trás do diagnóstico

> **Nota de empacotamento (FINAL-SUBMISSION-PACKAGE-01).** Este documento foi copiado do workspace de desenvolvimento sem alterar evidência. Os scripts citados estão em `solution/scripts/` e os outputs em `solution/outputs/`. Documentos de ciclos de desenvolvimento citados como fonte (ANALYSIS-08 a 16, AUDIT-01, docs numerados 09–21, `solution/outputs/environment_rerun/`) ficaram no workspace e não fazem parte do pacote; o que eles sustentam está consolidado aqui, no apêndice técnico e nos outputs incluídos.

Fonte de verdade analítica: `docs/FINAL-EVIDENCE-REGISTER.md`, com os números validados em `docs/19-solution-validation.md`. Todos os valores de MRR são **MRR proxy**: soma de `mrr_amount` por registro, sem moeda declarada no dataset (a única moeda explícita é `refund_amount_usd`).

## A1. O "aumento" de Q4 não excede o null calibrado

- As datas dos registros se ajustam a um mecanismo recuperado empiricamente (início ~ U[signup, fim]; encerramento ~ U[início, fim]; evento ~ U[signup, fim]). O código do gerador não está disponível; isto é o **melhor ajuste aos dados**.
- **Modelo anterior:** IRR de Q4 ajustada = 1,288 (p = 0,017). **Sob 1.000 datasets sem driver:** média 1,233, IC95 0,974–1,526, percentil 67; "significativo positivo" em 43,2% dos casos.
- **Encerramentos:** Q4 = 324 (null 296–365); dezembro = 193 (null 172–225); 31/12 = 24 (null 10–26).
- **Churn events em Q4/2024:** 251 observados contra 251,9 esperados pelo mecanismo; ajuste mês a mês nos 24 meses com p = 0,80.
- **Conclusão:** nenhuma evidência de excesso em Q4 acima do null calibrado.

## A2. Nenhum driver recuperável

- **89 testes de falsificação** (população completa, vazamento permitido): 0 com p < 0,05.
- **39 testes de segmento:** os 4 que passaram no FDR são propriedade do mecanismo de datas ou não replicam (indústria: p = 0,36 com cluster; país: p ≈ 0,07–0,09).
- **15 modelos** (logística, árvore, random forest, gradient boosting; 3 desfechos; mais de 100 variáveis com as 40 features abertas), cada um contra o próprio null por permutação: AUC fora da amostra entre 0,449 e 0,538, nenhum acima do null de forma robusta. Fontes reproduzíveis:
  - ANALYSIS-14, 9 modelos: `solution/scripts/end_to_end_sweep.py` → `solution/outputs/end_to_end_sweep/predictive_permutation_null.csv` (AUC fora da amostra 0,454–0,538; menor p de permutação 0,059);
  - ANALYSIS-15, 6 modelos: `solution/scripts/unblocked_models.py` → `solution/outputs/unblocked_models/ensemble_tests.csv` (AUC média de 5 sementes 0,449–0,515; menor p de permutação 0,22);
  - reexecução de reprodutibilidade: ver A3.
- **GEE com 21 fatores e cluster por conta:** nenhum q < 0,10; correlação dentro da conta ≈ −0,007.
- **Reason codes:** 15–19% cada; sem coerência com o comportamento (support × tickets p = 0,82; features × erros p = 0,98; pricing × MRR p = 0,68) nem com o feedback textual (A2d).
- **CSAT:** varia entre meses (p ≈ 0,005), sem padrão sazonal, persistente ou ligado a churn.
- **Contexto externo:** país, indústria e as condições de mercado testadas não deram explicação robusta para o churn.

## A2b. Taxas observadas por segmento (descritivo, não validado)

| Métrica | Valor |
|---|---|
| Taxa geral de `churn_flag` | 22,0% |
| Dimensões testadas (χ² por dimensão; FDR de Benjamini-Hochberg entre as 7) | indústria, país, canal, plano, trial, faixa de seats, coorte de signup |
| Dimensões com p < 0,05 | **0** |
| Menor q | **0,28** (indústria e canal) |

Alvo: `accounts.churn_flag`. Regra pré-definida: N ≥ 30 contas. Média geral: 110 / 500 = 22,0%. Maiores taxas (IC de Wilson a 95%):

| Segmento | Churned / total | Taxa | IC 95% | Veredito |
|---|---|---|---|---|
| DevTools | 35 / 113 | 31,0% | 23,2–40,0% | OBSERVED — NOT VALIDATED AS HIGHER RISK |
| Canal event | 29 / 96 | 30,2% | 21,9–40,0% | OBSERVED — NOT VALIDATED AS HIGHER RISK |
| 2023H1 | 29 / 109 | 26,6% | 19,2–35,6% | OBSERVED — NOT VALIDATED AS HIGHER RISK |
| Trial | 25 / 97 | 25,8% | 18,1–35,3% | OBSERVED — NOT VALIDATED AS HIGHER RISK |
| 6–15 seats | 33 / 134 | 24,6% | 18,1–32,6% | OBSERVED — NOT VALIDATED AS HIGHER RISK |

**Alemanha (DE):** 8 / 25 = 32,0% (IC 17,2–51,6%). Excluded from the ranking by the pre-defined N ≥ 30 rule. O mesmo segmento não aparece de forma robusta em nenhum dos outros testes: GEE, modelos e taxa por assinatura (registro F-08).

Uso permitido: **QUALITATIVE DISCOVERY OVERSAMPLE** nas entrevistas de saída. These segments are where the observed rate is highest, but the difference is not robust enough to direct retention spend. Uso proibido: campanha de retenção, "alto risco", "maior propensão". Fonte: `solution/outputs/auditor_integration/segment_observed_rates_final.csv`.

## A2c. Suporte sem tickets temporalmente inválidos (sensibilidade)

1.077 de 2.000 tickets (53,9%) têm `submitted_at` anterior ao `signup_date` da conta. Removidos esses tickets (restam 923), média por conta entre as contas com ≥ 1 ticket restante (89 flagged, 285 demais):

| Métrica | `churn_flag` = true | Demais | Mann-Whitney p |
|---|---|---|---|
| Tickets | 2,43 | 2,48 | 0,92 |
| First response (min) | 88,8 | 89,8 | 0,95 |
| Resolução (h) | 34,4 | 35,8 | 0,55 |
| Taxa de escalação | 7,0% | 5,5% | 0,86 |
| CSAT | 4,03 | 3,94 | 0,31 |

**Support remains non-separating even after correcting the obvious temporal inconsistency.** Fonte: `solution/outputs/auditor_integration/support_post_signup_sensitivity.csv`.

## A2d. Reason code × feedback textual

- 600 churn events; **452** com `feedback_text` preenchido. Só existem **3 textos distintos**: "too expensive", "missing features", "switched to competitor".
- Teste de independência `reason_code` × `feedback_text` nos 452: χ² = 3,83, 10 g.l., **p = 0,955** (permutação, 5.000 sorteios: p = 0,958); V de Cramér = 0,065.
- Exemplos: dos 136 "switched to competitor", só 21 têm `reason_code = competitor`; dos 155 "missing features", só 27 têm `features`; dos 161 "too expensive", 53 têm `pricing` ou `budget`. Cada texto se espalha pelos seis códigos (budget, competitor, features, pricing, support, unknown) em proporções de 13% a 20%.
- Conclusão permitida: **nem a variável destinada a registrar por que o cliente saiu apresenta coerência detectável com o feedback textual registrado.** Não se afirma que o código esteja "errado" em todos os casos.
- Nota de reprodução: o auditor reportou p ≈ 0,986. Esse valor reproduz quando os 148 eventos sem feedback entram como categoria "vazio" (n = 600, p = 0,986). Usamos o teste nos 452 textos preenchidos; a conclusão é a mesma.
- Fonte: `solution/outputs/auditor_integration/reason_feedback_alignment.csv`.

## A2e. Qualidade temporal de uso e suporte

| Verificação | Linhas | Total | % | Status |
|---|---|---|---|---|
| Uso dentro da vida observada da assinatura vinculada (`start_date` ≤ `usage_date` ≤ `end_date`, fim aberto permitido) | 5.568 | 25.000 | 22,27% | PARTIAL |
| Uso anterior ao signup da conta | 13.198 | 25.000 | 52,8% | WARNING |
| Ticket anterior ao signup da conta | 1.077 | 2.000 | 53,9% | WARNING |

Consequência: qualquer feature comportamental (uso, erros, suporte) está temporalmente desalinhada do lifecycle e não serve como antecedente de churn sem reconstrução. Fonte: `solution/outputs/auditor_integration/temporal_data_quality.csv`.

## A2f. Semântica das assinaturas

- **`subscriptions.churn_flag` não é um target independente.** 486 assinaturas têm `churn_flag = true`, e exatamente as mesmas 486 têm `end_date`; nenhuma com `churn_flag = false` tem `end_date`. At subscription grain, churn_flag is effectively a duplicate representation of subscription end. Por isso não é contado como uma quinta definição.
- **Registros simultâneos.** No fim da observação há 4.514 registros ativos, média de **9,0 por conta** (mediana 9). **418 / 500** contas têm registros ativos de Basic, Pro e Enterprise ao mesmo tempo; 496 / 500 têm dois ou mais planos ativos.
- Conclusão: o schema não estabelece que cada registro de assinatura corresponda um a um a um contrato comercial. Subscription line semantics are not equivalent to a validated commercial contract; portanto, **fim de assinatura ≠ perda de cliente**.
- Fonte: `solution/outputs/auditor_integration/subscription_semantics.csv`.

## A2g. Denominador do uso por conta ativa

```
Uso por conta ativa (período P) =
  soma(feature_usage.usage_count com usage_date em P)
  ÷ nº de account_id distintos com ≥ 1 registro de assinatura em que
    start_date ≤ fim(P) e (end_date vazio ou end_date > fim(P))
```

- Active account = account with ≥ 1 subscription record active at the period-end date.
- Numerador: todas as linhas de uso datadas no período, ligadas à conta via `subscription_id`; **não** são filtradas pela vida da assinatura (A2e).
- Cortes por segmento (indústria, país, plano): numerador e denominador restritos às contas cujo atributo na tabela `accounts` é o segmento.
- Períodos: comparação 2023H2 × 2024H2 (fins em 31/12/2023 e 31/12/2024: 190 e 500 contas ativas); tabela trimestral com fim no último dia do trimestre.
- Mesma regra em `solution/scripts/final_rewrite_build.py` (`act_accounts`) e `solution/scripts/end_to_end_sweep.py` (`accounts_with_active_sub_eom`). Definição em `solution/outputs/auditor_integration/usage_denominator_definition.json`.
- A direção (queda) se mantém; o percentual depende dessa definição de conta ativa.

## A2h. O que sabemos e o que não sabemos

| Sabemos | Não sabemos |
|---|---|
| Os três sinais de churn discordam | Por que um cliente individual realmente sai |
| A qualidade temporal de uso e suporte é baixa | A data comercial real de renovação |
| `reason_code` é semanticamente inconsistente | A perda real no nível de contrato |
| Não há sinal preditivo robusto | O efeito causal de qualquer ação de retenção |
| Alguns segmentos têm taxa observada maior | |
| As filas de ação são operacionalmente válidas | |

## A3. Reprodutibilidade

- O Smart App Control do Windows bloqueava 13 binários Python. O ambiente foi movido e as versões fixadas.
- 7 pipelines reexecutados e comparados célula por célula: nenhuma diferença material; nenhum dos 179 arquivos originais alterado.
- Os 15 modelos (ANALYSIS-14 e 15) foram reexecutados de novo na integração do auditor: 54/54 células idênticas, diferença máxima 0 (`solution/outputs/auditor_integration/model_rerun_comparison.csv`).
- Achados do auditor independente recalculados dos CSVs brutos: 52/53 reproduzidos, 1 conflito de definição de teste documentado em A2d (`solution/outputs/auditor_integration/auditor_findings_validation.csv`).

## A4. Piloto de renovação (desenho corrigido)

| Elemento | Desenho |
|---|---|
| População | V3 − V2 − V3-W1 = **314 contas**, com 1.045.553 de MRR proxy exposto. Exclui as contas que já recebem cobertura de valor ou o contato da primeira onda (contaminação) |
| Sorteio | 157 / 157, por conta, **antes de qualquer contato com o cliente** |
| Estratos | Tercil de MRR proxy exposto; billing; pertencer ou não à V1 |
| Data de renovação | Capturada por **fonte interna** (contrato, billing) nos dois braços, antes do tratamento |
| Tratamento | Outreach de renovação: decisor, revisão de valor, intenção (intenção só neste braço) |
| Controle | Rotina atual |
| **Primary business outcome** | Renovação ou não renovação no vencimento contratual |
| **Secondary business outcome** | MRR proxy retido; contraction |
| **Operational leading metrics** | Data de renovação capturada; decisor mapeado; reunião feita; intenção registrada |
| Guardrails | Tickets; downgrade/contraction; cancelamento antecipado |
| Janela | 90 dias = **lançamento**. A leitura acontece quando um N pré-registrado de contratos tiver vencido |
| Análise | Intention-to-treat |

**Poder** (bicaudal, α = 0,05, 157 por braço; taxa de base **hipotética**):

| Não renovação de base (premissa) | Efeito absoluto detectável com ~80% de poder |
|---|---|
| 10% | ~7,4 pp |
| 15% | ~9,4 pp |
| 20% | ~11,0 pp |

> Under these assumptions, the design has approximately 80% power only for absolute effects approximately this large. The baseline rate is an assumption, not observed data.

## A5. Prontidão para health score

**Resultado: 0 GREEN · 2 PARTIAL · 8 RED.** Não construir agora.

| Item | Status |
|---|---|
| Objetivo único | RED |
| Alvo rotulado | RED |
| Eventos de renovação | RED |
| Janela ≥ 1 ciclo | RED |
| Uso ligado ao lifecycle | **PARTIAL** (22,27%) |
| Timing de suporte coerente | RED |
| Histórico financeiro | **PARTIAL** (proxy reconstruível, não consolidado) |
| Sinais de relacionamento | RED |
| Validação fora da amostra acima do baseline | RED (AUC ≈ 0,5) |
| Playbook com dono | RED |

## A6. Fontes que sustentam decisões

- **Churn parcial = contraction; fórmulas de logo churn, GRR e NRR:** ChartMogul (help e blog), SaaS Capital (2025).
- **Arquitetura de lifecycle:** Stripe docs, Salesforce Trailhead (contratos e emendas), Chargebee docs.
- **Timing de renovação** (checkpoints de 6/3 meses; plays de 90–120 dias): Gainsight Community, HubSpot.
- **Mirar por lift, não por risco:** Ascarza, *Journal of Marketing Research*, 2018.
- **Sensibilidade e switching values:** HM Treasury, *The Green Book* (edição 2022, links atualizados).
- **Cenário ≠ previsão:** Elrha HI Guide.
- **Reason codes de múltipla escolha:** Paddle, exit survey.

Nenhuma decisão material depende só de texto de resultado de busca. Registro completo em `research/solution-source-register.csv`.
