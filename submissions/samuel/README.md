# Submissão — Samuel Santos — Challenge 001

## Sobre mim

- **Nome:** Samuel Santos
- **LinkedIn:** https://www.linkedin.com/in/samuelscs-ops/
- **Challenge escolhido:** 001 — Diagnóstico de Churn

---

## Executive Summary

Cruzei as cinco tabelas da RavenStack, submeti cada achado a auditorias adversariais e reproduzi tudo em código. **A RavenStack está medindo eventos diferentes como churn.** Por isso, com os dados disponíveis, não conseguimos confirmar que o aumento dos eventos registrados representa aumento da perda real de clientes: três sinais de churn e uma checagem de estado observável dão quatro respostas diferentes (110, 352, 312 e 0 contas). Recomendo transformar o problema numa operação de verdade e triagem — definição canônica de churn, três filas nominais de prioridade de negócio (176 contas na primeira onda), lifecycle contratual instrumentado em 60 dias e um piloto controlado para medir efeito real. Construí, além do diagnóstico e da planilha de filas, o **Churn Truth Lab**: uma página interativa que abre direto no navegador, sem internet, e responde "qual churn acreditar" e "quais contas revisar agora e por quê" — sem nenhuma previsão.

### Em 2 minutos

| Pergunta | Resposta |
|---|---|
| **O que eu encontrei?** | **A RavenStack está medindo eventos diferentes como churn.** Três sinais de churn e uma checagem de estado observável dão quatro respostas: 110, 352, 312 e **0** contas. As 110 contas flagged ainda possuem registros de subscription ativos com MRR proxy positivo. |
| **Por que importa?** | O CEO reage a indicadores que não podem ser interpretados de forma confiável como perda de cliente. Product e CS observam métricas que, isoladamente, não permitem inferir retenção ou saúde do cliente. Os dados disponíveis não permitem determinar de forma confiável quem saiu, quanto valia a perda nem quando cada cliente renova. |
| **O que a RavenStack deve fazer?** | Fixar uma definição canônica de churn; reconciliar as 110 contas "churned"; dar dono às 50 maiores contas; capturar datas de renovação; instrumentar o lifecycle contratual; e só então medir intervenções com um piloto controlado. |
| **O que eu construí?** | Diagnóstico executivo; planilha com **três filas de ação nominais** (V1/V2/V3, 176 contas na primeira onda); o **Churn Truth Lab**; scripts Python reproduzíveis com testes automáticos. |

> **Unidade de valor:** todos os valores são **MRR proxy** (soma de `mrr_amount` por registro). O dataset não declara moeda e os registros se sobrepõem, então nenhum valor é receita consolidada.

---

## Solução

### Abordagem

1. **Estrutura antes de análise:** grão, chaves, temporalidade, targets, leakage e denominadores das 5 tabelas foram tratados como pré-condição — antes de procurar qualquer "driver de churn".
2. **Cruzamento das tabelas:** Product, Support, contrato, segmento e motivos, um a um e em conjunto; modelos preditivos usados como teste de falsificação, não como produto.
3. **Auditoria adversarial:** IAs independentes tentaram derrubar as conclusões; um sinal de Q4 aparentemente significativo foi rejeitado por um null calibrado (ver Process Log).
4. **Soluções só depois:** pesquisa de soluções em fontes de mercado e validação independente dos números antes de escrever a entrega.

### Resultados / Findings

**Causa raiz de gestão.** Os dados não sustentam um target confiável de perda de cliente: flags, eventos e fins de assinatura identificam populações diferentes. **Causa do cancelamento individual.** Não identificável nas cinco tabelas — uso, suporte, plano, preço, aquisição, país e indústria não separam de forma robusta as populações identificadas pelos sinais de churn disponíveis.

**Três sinais de churn. Uma checagem de estado observável. Quatro respostas diferentes.**

| Sinal / checagem | Contas |
|---|---|
| `accounts.churn_flag = true` | 110 |
| Alguma conta com churn event | 352 |
| Alguma assinatura encerrada | 312 |
| Checagem de estado observável: sem nenhum registro ativo no fim de 2024 | 0 |

Sobreposições: flag ∩ evento = 75 · flag ∩ encerramento = 72 · evento ∩ encerramento = 227 · nas três = 50. Sob o estado contratual observável dos registros entregues, nenhuma conta termina 2024 sem registro ativo. Isso não significa ausência de perda real: significa que o estado contratual observável não permite identificar de forma confiável perda completa da conta. Além disso, o schema não estabelece que cada registro de assinatura corresponda a um contrato comercial validado: há em média ~9,0 registros ativos por conta, e 418 / 500 contas têm Basic, Pro e Enterprise ativos ao mesmo tempo.

**CEO × Product × CS**

| Área | Afirmação | Achado |
|---|---|---|
| CEO | "O churn aumentou" | Os eventos registrados sobem, mas não estabelecem maior propensão de perda. A subida não excede o que a estrutura de datas dos registros produz |
| Product | "O uso aumentou" | Total estável (30.789–32.227 por trimestre). Por conta ativa¹: **queda em 15/15 segmentos** (−40% a −77%) |
| CS | "Satisfação saudável" | 41,25% sem resposta; notas só de 3 a 5; sem relação com churn nem com a operação de suporte |

¹ **Uso por conta ativa** = soma de `usage_count` no período ÷ nº de contas com ≥ 1 registro de assinatura ativo na data de fim do período (`start_date` ≤ fim e `end_date` vazio ou posterior ao fim). Mesma regra em todos os documentos e no Truth Lab.

#### As quatro perguntas do challenge

**1. Uso × churn.** Contas com `churn_flag` × demais, média por conta: eventos de uso 522 × 495; features distintas 28,3 × 27,4; erros 28,2 × 28,2; erros por uso 0,054 × 0,057. Nenhuma separação validada.

**2. Suporte × churn.** Tickets 3,9 × 4,0; first response 84,9 × 89,6 min; resolução 35,5 × 36,5 h; CSAT 4,00 × 3,95. Nenhuma separação validada; prioridade não altera o tempo de resolução. Mesmo após remover tickets temporalmente inválidos (anteriores ao signup), suporte continua sem separar contas flagged das demais.

**3. O uso cresceu em todos os segmentos?** **Não.** Uso por conta ativa¹, 2º semestre de 2023 → 2º semestre de 2024: queda em todas as 5 indústrias, 7 países e 3 planos (−40% a −77%; tabela completa no [apêndice técnico](docs/TECHNICAL-APPENDIX.md) e no Truth Lab). **Atenção à qualidade temporal:** só 22,27% das linhas de uso caem dentro da vida observada da assinatura, e 52,8% das linhas de uso e 53,9% dos tickets são anteriores ao signup da conta. A direção da queda se sustenta, mas a telemetria precisa ser revista antes de qualquer leitura comportamental.

**4. Todo churn tem o mesmo peso?** Não. Concentração do MRR proxy ativo: top 10 contas = 8,4%; top 20 = 14,3%; top 50 = 27,4%; ranks 51–150 = 28,8%; ranks 151–500 = 43,8%. Enterprise representa 74,3% do MRR proxy ativo, mas a chance de uma assinatura terminar não difere por plano (p = 0,888) e 474/500 contas têm algum registro Enterprise ativo (461 com MRR proxy > 0). **Enterprise não serve como segmento de risco**; para priorização operacional imediata, a concentração de valor é mais útil.

#### Segmentos: onde a taxa observada é maior (observado, **não validado**)

Alvo: `accounts.churn_flag`. Regra pré-definida: só segmentos com N ≥ 30 contas. Média geral = **110 / 500 = 22,0%**.

| Segmento | Churned / total | Churn observado | IC 95% (Wilson) | Teste da dimensão | Veredito |
|---|---|---|---|---|---|
| Indústria **DevTools** | 35 / 113 | **31,0%** | 23,2%–40,0% | p = 0,066 · q = 0,28 | OBSERVED — NOT VALIDATED AS HIGHER RISK |
| Canal **event** | 29 / 96 | **30,2%** | 21,9%–40,0% | p = 0,079 · q = 0,28 | OBSERVED — NOT VALIDATED AS HIGHER RISK |
| Coorte de signup **2023H1** | 29 / 109 | 26,6% | 19,2%–35,6% | p = 0,27 · q = 0,62 | OBSERVED — NOT VALIDATED AS HIGHER RISK |
| **Trial** | 25 / 97 | 25,8% | 18,1%–35,3% | p = 0,39 · q = 0,68 | OBSERVED — NOT VALIDATED AS HIGHER RISK |
| **6–15 seats** | 33 / 134 | 24,6% | 18,1%–32,6% | p = 0,82 · q = 0,95 | OBSERVED — NOT VALIDATED AS HIGHER RISK |

Nenhuma dimensão atinge p < 0,05 e todos os intervalos se sobrepõem à média geral. **Alemanha (DE):** 8 / 25 = 32,0%, excluída pela regra N ≥ 30. **Uso recomendado: QUALITATIVE DISCOVERY OVERSAMPLE** — DevTools e o canal event entram como estratos a sobreamostrar nas entrevistas de saída, não como alvo de retenção.

**Motivo declarado de saída:** nos 452 churn events com feedback textual, `reason_code` não tem associação detectável com o texto (p = 0,955).

#### Contas específicas: três filas de prioridade de negócio

Lista nominal em [`solution/RavenStack_CS_Action_Queues.xlsx`](solution/RavenStack_CS_Action_Queues.xlsx) e no Truth Lab. **Business priority — not predicted churn risk.**

| Fila | Regra | Contas | MRR proxy |
|---|---|---|---|
| V1 Reconciliação de status | `churn_flag` = true e MRR proxy ativo > 0 | 110 (100% das flagged) | 2.073.153 (20,4% do ativo) |
| V2 Cobertura de valor | Top 50 por MRR proxy ativo | 50 | 2.781.650 (27,4% do ativo) |
| V3 Prontidão de renovação manual | Registros ativos sem auto-renew e com MRR proxy > 0 | 388 contas · 764 registros | 2.023.778 (19,9% do ativo) |
| V3-W1 (primeira onda da V3) | Top 50 por MRR proxy exposto | 50 contas · 137 registros | 873.996 (43,2% da V3) |
| **Onda de 30 dias** | V1 ∪ V2 ∪ V3-W1 | **176 únicas** (não 210: V1∩V2 = 9, V1∩V3-W1 = 11, V2∩V3-W1 = 17, nas três = 3) | — |

*Das 409 contas com algum registro ativo `auto_renew = false`, 21 possuem somente exposições `auto_renew = false` de trial com MRR proxy zero (essas 21 têm outras assinaturas pagas ativas). Excluindo essas exposições sem valor econômico, restam **388 contas e 764 registros** com MRR proxy positivo, totalizando 2.023.778 de MRR proxy.*

#### O que eu deliberadamente não construí

Nenhum modelo de churn, probabilidade, health score ou lista de "contas em risco". Os modelos preditivos testados (logística, árvore, random forest, gradient boosting, mais de 100 variáveis) não superaram de forma robusta seus respectivos nulls por permutação; os três sinais de churn discordam entre si; e mais da metade das linhas de uso e dos tickets é anterior ao signup da conta. Um modelo agora apontaria o CS para contas escolhidas por ruído. Prontidão para health score hoje: **0 GREEN · 2 PARTIAL · 8 RED**.

#### Churn Truth Lab — construído e validado

**Abra [`solution/truth-lab/index.html`](solution/truth-lab/index.html) com dois cliques.** Estático e offline (sem servidor, backend ou rede externa), 6 telas, interface em português:

| Tela | Conteúdo |
|---|---|
| 1. Verdade do churn | Três sinais + uma checagem de estado observável, sobreposição (UpSet), causa de gestão × causa individual, "Por que uma previsão não é suportada hoje" |
| 2. Denominador | Uso total × por conta ativa¹ × por assinatura, por segmento, com a fórmula ao lado da métrica; segmentos observados |
| 3. Filas de ação | V1, V2 e V3-W1, onda de 176, 409 → 21 → 388; tabela com busca, ordenação, filtro e exportação CSV |
| 4. Brief da conta | As 5 tabelas numa visão + flags descritivas de qualidade de dados + perguntas para o CSM |
| 5. Lab de impacto | Cenário 0–20% sobre a exposição V3, break-even com custo informado pelo usuário, cartão do piloto |
| 6. Confiança dos dados | Status por dimensão, prontidão para health score, semântica das assinaturas |

Todo número abre SOURCE, GRAIN, COVERAGE e LIMITATION (clique no **i**). Os números vêm pré-calculados dos outputs validados em Python; o navegador só calcula o break-even sobre o custo digitado. Suíte completa: 213/213 no Edge; autoteste 101/101 no Chrome, ambos com execução offline. Screenshots em [`process-log/screenshots/truth-lab/`](process-log/screenshots/truth-lab/).

### Recomendações

1. **Segunda-feira:** definição canônica de churn; reconciliar a V1 em 14 dias; donos para a V2; datas de renovação da V3-W1 por fonte interna.
2. **Motivo de saída (ação orientada pelos dados):** como `reason_code` não tem coerência detectável com o feedback textual, substituir os códigos por uma taxonomia com motivo principal + fatores contribuintes, resposta aberta, fonte e confiança, e entrevistas de saída.
3. **31–60 dias:** lifecycle contratual (`contract_id`, `product_id`, predecessor, `renewal_due_date`, datas de pedido e efetivação do cancelamento, classificação mensal de movimentos) e rotina de renovação.
4. **61–90 dias:** lançar um piloto controlado em 314 contas (V3 − V2 − V3-W1; 157 por braço). Ele não terá resultado em 90 dias; é lido no vencimento contratual.

**Impacto estimado, em três níveis:**
- **Fato:** 2.023.778 de MRR proxy em renovação manual.
- **Cenário condicional:** se uma intervenção preservar, no fim, 5%, 10% ou 15% dessa exposição, o valor associado seria de 101.189, 202.378 ou 303.567 de MRR proxy por mês. *Cenário, não previsão; nenhuma probabilidade atribuída; não existe estimativa causal.*
- **Efeito real:** só pelo piloto.

Detalhes no [diagnóstico executivo](solution/EXECUTIVE-DIAGNOSIS.md); evidência estatística no [apêndice técnico](docs/TECHNICAL-APPENDIX.md) e no [registro de evidências](docs/FINAL-EVIDENCE-REGISTER.md).

### Limitações

- O dataset é sintético e observacional; o código do gerador não está disponível.
- Um registro de assinatura não equivale necessariamente a um contrato validado.
- O MRR é proxy por registro e sem moeda declarada.
- Não existem `renewal_due_date`, `contract_id` nem `product_id`.
- A causa individual de cancelamento não é recuperável nestas tabelas — o que não prova que, no negócio real, não existam motivos.
- O ranking de soluções é julgamento de analista (pesos iguais, com sensibilidade), não um resultado estatístico.
- Truth Lab: desktop-first; mobile não testado formalmente; o estado de revisão V1 não persiste ao recarregar (sai no CSV); Edge e Chrome testados, Firefox e Safari não.

---

## Process Log — Como usei IA

Narrativa completa e cronológica em [`process-log/PROCESS-LOG.md`](process-log/PROCESS-LOG.md); construção do Truth Lab em [`process-log/TRUTH-LAB-BUILD.md`](process-log/TRUTH-LAB-BUILD.md).

### Ferramentas usadas

**Ferramentas de IA**

| Ferramenta | Para que usei |
|---|---|
| ChatGPT / OpenAI | Desenho dos prompts, metodologia, estrutura de red-team, revisão de aderência ao challenge, enquadramento das soluções, especificação do Truth Lab e revisão crítica |
| OpenAI Codex | Primeiras análises (estrutura, Feature Usage, Support, outcomes, risk set, lifecycle, causa raiz), código, primeira síntese e primeira submissão. ANALYSIS-16 (mercado): tool attribution not independently verified |
| Antigravity IDE / Claude Code (extensão `anthropic.claude-code`) | Auditoria adversarial independente, varredura das 5 tabelas, correção do ambiente e reexecução, governança de errata, pesquisa e validação de soluções, reescrita, integração do auditor, construção e fechamento do Truth Lab, empacotamento. Host verificado no ambiente: processo `claude.exe` da extensão, filho do `Antigravity IDE.exe` |
| Subagentes de pesquisa web (dentro do Claude Code) | 3 frentes de pesquisa de soluções (58 fontes), com regra de citar só páginas efetivamente abertas |

**Ferramentas de execução (não são IA):** Python 3.12 (pandas, numpy, scipy, statsmodels, scikit-learn, openpyxl) para pipelines, testes, simulações e planilha; PowerShell para execução e diagnóstico do ambiente Windows; Edge e Chrome headless para testar o Truth Lab.

### Workflow

**Uma iteração = um ciclo documentado de análise → validação/auditoria → decisão/alteração.** Há pelo menos **19 ciclos principais documentados** antes deste empacotamento (lista no Process Log). Em resumo:

1. **Estrutura e auditoria do dataset** — tabelas conectáveis, mas sem timeline coerente sem regras de elegibilidade temporal.
2. **Análises por área** (uso, suporte, outcomes, risk set, lifecycle) — nenhum driver robusto.
3. **Triangulação de causa raiz** — a IA classificou um aumento de Q4 (IRR 1,288; p = 0,017) como "associação real".
4. **Auditoria adversarial independente** — o mesmo "sinal" aparece em 43% de 1.000 datasets simulados sem causa; conclusão rejeitada, estratégia mudou de "achar o driver" para "a empresa mede churn errado".
5. **Varredura das 5 tabelas, reexecução em ambiente corrigido, mercado** — nulo confirmado por 15 modelos, GEE e séries temporais.
6. **Governança** — registro de evidências (F-01 a F-22) com redação permitida e proibida; erros antigos mantidos com errata.
7. **Auditoria de aderência ao challenge** — veredito "tecnicamente excelente, competitivamente médio"; a entrega foi reposicionada para a pergunta do CEO.
8. **Pesquisa e validação de soluções** — filas Q1/Q2/Q3 derrubadas sobre os dados brutos e substituídas por V1/V2/V3; mais 6 correções (incluindo piloto contaminado).
9. **Reescrita business-first** — moeda removida, 409 → 388, piloto em 314 contas.
10. **Auditor em chat limpo** — 52 de 53 números reproduzidos; achados temporais e semânticos novos incorporados só depois de recalculados.
11. **Truth Lab** — especificação, construção, QA visual, 213 testes, revisão humana e ajustes finais de redação.

### Onde a IA errou e como corrigi

- **Q4 tratado como associação real** → null calibrado com 1.000 simulações; rejeitado.
- **Proximidade de datas rotulada como upgrade/downgrade** → mesma taxa em dados aleatórios (23,0% × 24,4%); rótulos retirados.
- **Fila "Enterprise"** → 474/500 contas têm registro Enterprise; substituída por valor de conta.
- **Impacto calculado sobre "MRR encerrado"** → o MRR estava em contas ainda ativas; virou referência descritiva.
- **409 contas de exposição** → 388 (21 têm só exposição de trial com MRR zero).
- **Moeda (R$) atribuída a um valor sem moeda** → removida; "MRR proxy".
- **Piloto com controle contaminado** → população de 314 contas sem sobreposição.
- **"Quatro definições de churn"** → três sinais de churn + uma checagem de estado observável.
- **p-value do auditor (0,986)** → não reproduzia nos 452 feedbacks preenchidos; mantido o valor reproduzível (0,955), com o conflito documentado.

Cada erro foi detectado por uma etapa de verificação e corrigido com errata rastreável.

### O que eu adicionei que a IA sozinha não faria

- Exigi que a IA tentasse **derrubar** a própria resposta e recusei veredito apoiado só em "compatível com o null".
- Exigi análise direta das 5 tabelas e correção real do ambiente, em vez de contornos.
- Pedi auditoria de **aderência ao challenge** quando o trabalho estava tecnicamente certo, mas competitivamente fraco.
- Bloqueei entregáveis atraentes e falsos: churn probability, health score, Revenue at Risk, filas chamadas de risco.
- Levei a entrega a um auditor em chat limpo e exigi reprodução antes de incorporar — inclusive contra o auditor quando o número dele não reproduzia.
- **Regra de trabalho:** a IA propõe. O código executa. Os dados validam. O analista decide.

---

## Evidências

**Formato principal escolhido:** narrativa escrita (aceito pelo guia de submissão).

- [x] Narrativa escrita detalhada e cronológica em [`process-log/PROCESS-LOG.md`](process-log/PROCESS-LOG.md)
- [x] Construção e validação do Truth Lab em [`process-log/TRUTH-LAB-BUILD.md`](process-log/TRUTH-LAB-BUILD.md) e [`docs/TRUTH-LAB-VALIDATION.md`](docs/TRUTH-LAB-VALIDATION.md)
- [x] Scripts reproduzíveis em [`solution/scripts/`](solution/scripts/), com setup em [`solution/README.md`](solution/README.md)
- [x] Registro técnico de evidências em [`docs/FINAL-EVIDENCE-REGISTER.md`](docs/FINAL-EVIDENCE-REGISTER.md)
- [x] Screenshots do Truth Lab (produto, não conversas) em [`process-log/screenshots/truth-lab/`](process-log/screenshots/truth-lab/)
- [ ] Screenshots das conversas — não utilizado como formato principal
- [ ] Screen recording — não utilizado
- [ ] Chat exports — não utilizado

Checklist de submissão: [`docs/FINAL-SUBMISSION-CHECKLIST.md`](docs/FINAL-SUBMISSION-CHECKLIST.md).

### Conteúdo da pasta

```
submissions/samuel/
├── README.md                          ← este arquivo
├── solution/
│   ├── README.md                      ← como executar e reproduzir
│   ├── EXECUTIVE-DIAGNOSIS.md         ← diagnóstico para o CEO
│   ├── RavenStack_CS_Action_Queues.xlsx
│   ├── truth-lab/                     ← Churn Truth Lab (abrir index.html)
│   ├── scripts/                       ← pipelines e verificadores Python
│   ├── outputs/                       ← outputs validados (pequenos) usados pelos verificadores
│   ├── data/                          ← instruções + SHA-256 dos CSVs (dados não incluídos)
│   └── requirements.txt
├── process-log/                       ← narrativa do uso de IA + build do Truth Lab + screenshots do produto
└── docs/                              ← apêndice técnico, registro de evidências, requisitos, validação, checklist
```

---

_Submissão enviada em: 04/10/2026_
