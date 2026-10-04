# Process Log — Challenge 001 (RavenStack churn)

**Formato:** narrativa escrita. Todos os fatos abaixo vêm dos documentos e logs de desenvolvimento do projeto. Os nomes entre parênteses (ex.: ANALYSIS-13, AUDIT-01) identificam cada ciclo nesses registros. O conteúdo validado está neste pacote: `docs/FINAL-EVIDENCE-REGISTER.md`, `docs/TECHNICAL-APPENDIX.md` e `solution/scripts/`.

## 1. Como decompus o problema

Antes de procurar "drivers de churn", tratei sete coisas como pré-condição:

| Pré-condição | O que verifiquei |
|---|---|
| Grão | Conta, assinatura, linha de uso, ticket, evento |
| Chaves | `account_id` e `subscription_id` |
| Targets | O que conta como churn |
| Temporalidade | Datas de cada evento em relação ao lifecycle |
| Leakage | Variáveis posteriores ao desfecho |
| Denominadores | Por conta, por assinatura, por período |
| Lifecycle | Se registros encadeados formam um contrato |

A pergunta "por que os clientes saem?" só faz sentido depois de saber o que conta como "sair". Essa ordem salvou o projeto. A resposta final é exatamente essa: os dados não sustentam um target confiável de perda de cliente.

## 2. Ferramentas usadas

**Ferramentas de IA**

| Ferramenta | Onde entrou |
|---|---|
| **ChatGPT / OpenAI** | Desenho dos prompts de cada etapa, metodologia, estrutura de red-team, revisão de aderência ao challenge, enquadramento das soluções, especificação do Truth Lab e revisão crítica (confirmado por Samuel) |
| **OpenAI Codex** | Análises iniciais (estrutura, Feature Usage, Support, reconciliação de outcomes, risk set, revenue/lifecycle, triangulação de causa raiz), código Python, primeira síntese e primeira submissão. **ANALYSIS-16 (mercado):** tool attribution not independently verified |
| **Antigravity IDE / Claude Code** (extensão `anthropic.claude-code`) | Auditoria adversarial independente; varredura das 5 tabelas; diagnóstico e correção do ambiente Python; reexecução; governança de errata e registro de evidências; auditoria de aderência; pesquisa e validação de soluções; reescrita; integração do auditor independente; construção, QA e fechamento do Truth Lab; empacotamento. Host verificado no ambiente: processo `claude.exe` da extensão, filho do `Antigravity IDE.exe` |
| **Subagentes de pesquisa web** (dentro do Claude Code) | Pesquisa de soluções em 3 frentes paralelas (métricas e lifecycle; CS ops; VoC, experimentos e impacto), 58 fontes, com a regra de citar só páginas efetivamente abertas |
| **IA auditora em chat limpo** | Segunda opinião independente sobre a entrega pronta, partindo só dos CSVs (ciclo 17) |

**Ferramentas de execução (não são IA):**
- Python 3.12 com pandas, numpy, scipy, statsmodels, scikit-learn e openpyxl;
- PowerShell;
- Edge e Chrome headless, para os testes do Truth Lab.

## 3. Primeiras análises

Os primeiros ciclos cruzaram as tabelas área por área:

1. **Estrutura.** As tabelas são referencialmente conectáveis, mas não formam uma timeline coerente sem regras explícitas de elegibilidade temporal.
2. **Feature Usage × churn.** Não houve evidência suficiente de que o uso distinga churn. A cobertura válida era pequena.
3. **Support × churn.** Auditoria aprovada com ressalva semântica: "churn event" não é necessariamente perda de cliente.
4. **Reconciliação de outcomes.** A decisão foi separar dois desfechos: fim de assinatura e evento de churn.
5. **Risk set e revenue/lifecycle.** Valores intermediários inconsistentes foram encontrados e corrigidos por errata (ANALYSIS-11B).

Nenhuma área mostrou driver robusto. A dúvida passou a ser se isso era falta de sinal ou falta de método.

## 4. Primeiro grande erro da IA — Q4

| Etapa | O que aconteceu |
|---|---|
| Achado | A triangulação de causa raiz (ANALYSIS-13) viu as assinaturas encerrarem mais em Q4/2024: aumento de 29% no modelo Poisson (IRR 1,288; **p = 0,017**). A IA classificou isso como "associação real" e "deterioração no fim do período" |
| Contestação | Pedi uma auditoria para **derrubar** o trabalho. Uma segunda IA, partindo dos CSVs brutos, notou que as datas seguem um padrão de uniformes aninhadas que acumula eventos perto do fim do período |
| Falsificação | O mesmo modelo, rodado em 1.000 datasets simulados **sem nenhuma causa**, deu "aumento significativo" em 43,2% deles. O valor observado ficou no percentil 67: comum, não excepcional |
| Decisão | "Q4 real" foi rejeitado e virou errata nos documentos históricos, sem apagá-los |
| Consequência | A estratégia mudou de "achar o driver" para "a empresa mede churn de um jeito que não permite saber quem saiu" |

Esse foi o momento de julgamento que definiu o projeto. Um p-value baixo não basta: ele precisa ser comparado ao que o próprio processo gerador dos dados produz.

## 5. Outros erros e correções

| Erro da IA | Como foi detectado | Correção |
|---|---|---|
| Proximidade de datas rotulada como upgrade/downgrade | A mesma regra aplicada a dados aleatórios dá a mesma taxa (23,0% × 24,4%) | Rótulos retirados |
| Churn de conta "impossível de calcular" | Timeline diária por conta | Calculado: 0 contas sem registro ativo, sem confundir com perda comercial |
| Ausência de telemetria tratada como uso zero | Revisão de código | Documentado; nulo confirmado por outros testes |
| Regressão logística manual sem checagem de convergência | 40 modelos refeitos com statsmodels | Diferença máxima de 4,5×10⁻⁶; sem impacto |
| Ambiente com bibliotecas bloqueadas pelo Windows (Smart App Control) | Logs de integridade do sistema | Ambiente movido e versões fixadas; 7 pipelines reproduzidos célula por célula |
| Fila "Enterprise" como prioridade | Contagem nos dados brutos: 474/500 contas têm registro Enterprise | Substituída por concentração de valor |
| Impacto calculado sobre "MRR encerrado" | O MRR encerrado estava em contas ainda ativas | Virou referência descritiva, não perda |
| Moeda (R$) atribuída ao MRR | Revisão do schema: o dataset não declara moeda | Removida; "MRR proxy" |
| 409 contas de exposição | Validação independente | 388 (21 têm só exposição de trial com MRR zero e outras assinaturas pagas) |
| Piloto com grupo de controle contaminado | Validação independente | População de 314 contas sem sobreposição com as filas |
| "As 110 flagged continuam pagando" | Auditor independente (afirmação comercial não verificável) | "Ainda possuem registros de subscription ativos com MRR proxy positivo" |
| "Quatro definições de churn" | Auditor | Três sinais de churn + uma checagem de estado observável |
| Uso por conta citado sem denominador | Auditor | Regra lida no código e escrita ao lado da métrica em todos os documentos |
| Range de AUC na narrativa principal | Auditor | README diz "não superaram o null"; valores exatos só no apêndice |
| Verificador acusou "53,8%" onde o texto diz 53,9% (1.077/2.000 = 53,85%) | Execução do verificador | Arredondamento decimal exato em vez do artefato de ponto flutuante |

## 6. Auditoria independente em chat limpo

| Etapa | O que aconteceu |
|---|---|
| Auditor | Uma IA em chat limpo, sem o histórico do projeto, recebeu os 5 CSVs e recalculou os números centrais. Veredito: STRONG, 88/100 |
| Reprodução | Confirmou exatamente 110 / 352 / 312 / 0, as sobreposições, V1, V2, V3, V3-W1 e a onda de 176 |
| Achados novos | Qualidade temporal: 52,8% do uso e 53,9% dos tickets são anteriores ao signup; só 22,27% do uso cai dentro da vida da assinatura. Semântica: `reason_code` sem relação com o feedback textual; ~9 registros ativos por conta; `subscriptions.churn_flag` idêntico a `end_date` |
| Regra adotada | Nada do auditor entrou sem ser recalculado dos CSVs brutos por código próprio (`solution/scripts/auditor_integration.py`). **52 de 53 valores bateram** |
| Conflito | Para `reason_code` × feedback, o auditor reportou p ≈ 0,986. Esse valor só reproduz contando o feedback vazio como categoria (n = 600). Nos 452 feedbacks preenchidos, a reprodução correta dá **p = 0,955**. Mantive o resultado reproduzível, não a autoridade do auditor, e documentei o conflito. A conclusão (nenhuma associação) é a mesma |
| O que não mudou | A tese central. Os achados novos a reforçam |

## 7. Decisões que tomei

- Não aceitar associação como causalidade (Q4).
- Não criar churn probability sem um target confiável.
- Não criar health score: a prontidão é 0 GREEN · 2 PARTIAL · 8 RED.
- Não criar Revenue at Risk e não chamar as filas V1/V2/V3 de risco de churn.
- Construir **prioridade operacional** com regra declarada: reconciliação de status, cobertura de valor e prontidão de renovação.
- Medir efeito real só com **piloto controlado** (314 contas, 157 / 157, pré-registrado).
- Manter todos os erros históricos com errata, em vez de apagá-los.
- Pedir uma auditoria de **aderência ao challenge** quando o trabalho estava tecnicamente certo, mas competitivamente médio. Essa auditoria mudou a manchete para a pergunta do CEO.

## 8. Construção do Truth Lab

| Aspecto | Como foi feito |
|---|---|
| Motivo | O CEO precisava ver qual número de churn acreditar, e o CS precisava saber em quem agir, sem nenhuma previsão |
| Especificação | Requisitos com rótulos obrigatórios e frases proibidas (`docs/TRUTH-LAB-REQUIREMENTS.md`), revisados após o auditor independente |
| Implementação | HTML, CSS e JavaScript puros; gráficos SVG desenhados à mão; 6 telas; abre por `file://`, offline, sem backend |
| Dados | Pré-calculados em Python (`solution/scripts/build_truth_lab_data.py`) a partir dos outputs validados, com verificação contra eles antes de gravar. O navegador não recalcula nada analítico; só calcula o break-even sobre o custo digitado |
| QA visual | Screenshots headless de cada tela revelaram 10 defeitos visuais, corrigidos e conferidos de novo |
| Restrições de wording | Teste automático de frases proibidas. Dois conflitos internos do prompt de construção foram resolvidos por regra declarada: o rótulo obrigatório "Business priority — not predicted churn risk" contém uma frase proibida, e a dimensão "Revenue history" virou "Histórico financeiro" |
| Revisão humana | Aprovou a estrutura e pediu interface coerente em português e redação menos dramática ("unsafe", "at stake"). Aplicado sem redesenho |

Detalhes em `TRUTH-LAB-BUILD.md`.

## 9. Validação final

| Verificação | Resultado |
|---|---|
| `check_truth_lab.py` | **213/213** testes: numéricos 78, metadados, frases proibidas e moeda, offline estático, arquivos e 102 funcionais, com a página rodando em Edge headless e com a rede desligada |
| Chrome | Autoteste 101/101 |
| `closeout_check.py` (varredura de frases antigas no conteúdo atual) | **0 MUST FIX**. Testes negativos confirmam que cada padrão é detectado |
| Afirmações numéricas dos documentos contra os outputs | 55/55 e 40/40 |
| Reexecução dos 15 modelos preditivos | **54/54 valores idênticos**. A "falha" aparente da ANALYSIS-15 veio de um comando no fim do script, não da execução dos modelos |
| Limpeza final de redação executiva | Frase do CEO, interpretação das zero contas, p = 0,955, Enterprise, atribuição de ferramenta. Nenhum número alterado |

## Matriz de evidências do processo

Onde cada decisão importante pode ser verificada dentro deste pacote. Caminhos relativos a `submissions/samuel/`. "Registro" = `docs/FINAL-EVIDENCE-REGISTER.md`.

| Ciclo / decisão | Papel da IA | Evidência reproduzível | Validação | Decisão humana |
|---|---|---|---|---|
| 1. Estrutura e definição de outcomes | Mapeou grão, chaves e desfechos das 5 tabelas | `solution/outputs/independent_audit/account_outcome_definitions.csv`; `solution/outputs/final_rewrite/final_numbers.json`; Registro F-01, F-03 | 110 / 352 / 312 / 0 reproduzidos pelo auditor externo e conferidos por `final_rewrite_check.py` | Tratado como três sinais de churn + uma checagem de estado observável, não como uma taxa de churn única |
| 2. Q4 aparentemente significativo | Encontrou IRR 1,288 (p = 0,017) e o classificou como "associação real" | `solution/outputs/independent_audit/q4_null_calibration.csv` (linha `IRR_Q4_COMPOSITION_PLUS_START_COHORT`) | — | Não aceito sem teste contra o processo gerador dos dados |
| 3. Falsificação do Q4 | Uma segunda IA, em auditoria adversarial, notou o padrão de datas que acumula eventos no fim do período | `solution/scripts/independent_audit.py` → `q4_null_calibration.csv` e `q4_null_draws.csv` (1.000 simulações); Registro F-02 | 43,2% dos datasets sem causa dão "aumento significativo"; percentil 67; reexecução byte a byte idêntica | **Rejeitado**; errata nos documentos históricos |
| 4. Upgrade/downgrade | Rotulou proximidade de datas como movimento de lifecycle | `solution/outputs/independent_audit/lifecycle_links_vs_chance.csv`; Registro F-05 | 23,0% observado × 24,4% em dados aleatórios | **Rótulos retirados** |
| 5. Fila "Enterprise" | Propôs Enterprise como fila prioritária | `solution/outputs/final_rewrite/final_numbers.json` (bloco `enterprise`) | 474/500 contas têm registro Enterprise; p = 0,888 entre planos | **Removida como fila**; substituída por concentração de valor (V2) |
| 6. "MRR encerrado" como perda | Calculou impacto sobre o MRR de registros encerrados | `solution/outputs/final_rewrite/final_numbers.json` (bloco `ended_2024`) | 100% do MRR encerrado em 2024 estava em contas ainda com registros ativos | **Mantido só como referência descritiva** |
| 7. 409 → 388 | Usou 409 contas / 899 registros como exposição | `solution/outputs/final_rewrite/final_numbers.json`; `solution/RavenStack_CS_Action_Queues.xlsx`; Registro F-16 | 21 contas só com exposição de trial com MRR zero; planilha conferida (388 linhas na V3) | **Corrigido para 388 / 764**, com errata do F-16 |
| 8. p ≈ 0,986 do auditor | O auditor externo reportou p ≈ 0,986 | `solution/scripts/auditor_integration.py` → `solution/outputs/auditor_integration/auditor_findings_validation.csv` (linha R2) e `reason_feedback_alignment.csv`; Registro F-20 | Reprodução: p = 0,955 em 452 feedbacks; 0,986 só com os vazios como categoria | **Só incorporado após reprodução**; mantido 0,955, conflito documentado |
| 9. Segmentos com taxa maior | Calculou taxas observadas por segmento | `solution/outputs/auditor_integration/segment_observed_rates_final.csv`; `solution/outputs/final_rewrite/observed_segment_rates.csv` | Nenhuma dimensão com p < 0,05; todos os ICs sobrepõem a média | **Rotulado** "observed — not validated"; usado só para sobreamostragem qualitativa, **não para risk targeting** |
| 10. Piloto 314 (157 + 157) | Desenhou o piloto; a primeira versão tinha controle contaminado | `solution/outputs/final_rewrite/final_numbers.json` (bloco `pilot`) | Validação independente apontou a sobreposição com as filas; MDE ~7,4 / 9,4 / 11,0 pp | População sem sobreposição; efeito real **só pelo piloto** |
| 11. Truth Lab | Especificou, construiu e testou a página | `solution/scripts/build_truth_lab_data.py`; `solution/scripts/check_truth_lab.py`; `solution/outputs/truth_lab/truth_lab_checks.csv` | 213/213 no Edge; autoteste 101/101 no Chrome; offline | Previsão, health score e Revenue at Risk **bloqueados como produto**; filas como **prioridade operacional** |
| 12. Validação final | Rodou os verificadores e a reprodução do pacote | `docs/TRUTH-LAB-VALIDATION.md` (Parte C); `solution/outputs/auditor_integration/model_rerun_comparison.csv` | 55/55, 40/40, 0 MUST FIX, 95/95; pipelines byte a byte idênticos; 54/54 valores de modelos idênticos | Entrega publicada só depois de todos os verificadores passarem |

Leitura da matriz: a IA encontrou hipóteses e também as auditou; o código reproduziu os números; Samuel decidiu o que entrava ou não na entrega.

## 10. Iterações e resultado

**Definição:** uma iteração é um ciclo documentado de análise → validação/auditoria → decisão/alteração. Contei só ciclos com registro escrito, não prompts individuais. Há **pelo menos 19 ciclos principais documentados** antes deste empacotamento:

1. Briefing, auditoria do dataset e auditoria estrutural.
2. Feature Usage × churn.
3. Support × churn.
4. Reconciliação de outcomes.
5. Validação do risk set (ANALYSIS-11B).
6. Revenue e lifecycle contratual.
7. Triangulação de causa raiz (Q4 "real").
8. Auditoria adversarial independente (AUDIT-01: Q4 rejeitado).
9. Varredura de ponta a ponta das 5 tabelas.
10. Ambiente corrigido e reexecução (7 pipelines, ensembles, GEE, séries temporais).
11. Mercado e síntese executiva.
12. Correções finais e registro de evidências (FINAL-CORRECTIONS-02, 20/20 PASS).
13. Auditoria de aderência ao challenge.
14. Pesquisa de soluções.
15. Validação das soluções.
16. Reescrita final business-first.
17. Integração do auditor em chat limpo (e errata do F-16).
18. Construção do Truth Lab.
19. Fechamento do Truth Lab e limpeza final de redação.

Pode haver ciclos curtos não registrados, sobretudo nas primeiras conversas. Por isso o número é um mínimo.

**Resultado:** um diagnóstico que responde à pergunta do CEO com o que os dados sustentam, três filas acionáveis, um piloto para medir efeito real e um Truth Lab que mostra a evidência sem prever nada.

**Regra de trabalho: a IA propõe. O código executa. Os dados validam. O analista decide.**
