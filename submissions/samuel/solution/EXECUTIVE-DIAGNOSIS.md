# RavenStack — Diagnóstico executivo de churn

> **Unidade de valor:** todos os valores são **MRR proxy**, a soma do `mrr_amount` dos registros de assinatura. O dataset não declara moeda e os registros se sobrepõem, então nenhum valor aqui é receita consolidada.

## 1. Manchete

**A RavenStack está medindo eventos diferentes como churn.**

Por isso, com os dados disponíveis, não conseguimos confirmar que o aumento dos eventos registrados representa aumento da perda real de clientes. A empresa não consegue determinar com confiabilidade quem realmente saiu, quanto valia essa perda e quando cada cliente renova. É por isso que o "churn subindo" do CEO não leva a nenhuma ação clara.

## 2. O que está realmente acontecendo

**Três sinais de churn. Uma checagem de estado observável. Quatro respostas diferentes.**

| Sinal / checagem | Contas (de 500) |
|---|---|
| `accounts.churn_flag = true` | **110** |
| Conta com algum churn event | **352** |
| Conta com alguma assinatura encerrada | **312** |
| Checagem de estado observável: conta que termina 2024 sem nenhum registro ativo | **0** |

Os três sinais quase não se sobrepõem: flag ∩ evento = 75; flag ∩ encerramento = 72; evento ∩ encerramento = 227; nas três = 50.

- **As 110 contas flagged ainda possuem registros de subscription ativos com MRR proxy positivo,** somando 2.073.153 de MRR proxy (20,4% do MRR proxy ativo).
- **Encerrar uma assinatura não é perder o cliente:** 98,7% do MRR proxy das assinaturas encerradas em 2024 estava em contas que já tinham outro registro ativo logo após o encerramento.
- Sob o estado contratual observável dos registros entregues, nenhuma conta termina 2024 sem registro ativo. Isso **não** significa ausência de perda real: significa que o estado contratual observável não permite identificar de forma confiável perda completa da conta.

**Causa raiz:** os dados não sustentam um target confiável de perda de cliente. Flags de conta, eventos de churn e fins de assinatura identificam populações materialmente diferentes, enquanto as tabelas de lifecycle e comportamento também apresentam inconsistências temporais e semânticas importantes. Em duas perguntas:

- **Por que o CEO vê o churn subir?** O KPI mistura eventos de grãos diferentes (flag de conta, evento, fim de assinatura) sem um lifecycle contratual reconciliado. Essa é a causa raiz do **problema de gestão**. A subida de eventos no fim de 2024 não fica acima do que a própria estrutura de datas dos registros produz (apêndice técnico).
- **Por que um cliente individual sai?** Não é identificável nas cinco tabelas. Uso, suporte, plano, preço, seats, aquisição, país e indústria não separam de forma robusta as populações identificadas pelos sinais de churn disponíveis, nem combinados num modelo.

Dois achados reforçam a tese:

- **A qualidade dos dados também bloqueia a leitura comportamental:** 52,8% das linhas de uso e 53,9% dos tickets são anteriores ao signup da conta. Mesmo removendo os tickets inválidos, suporte continua sem separar contas flagged das demais.
- **Até o motivo declarado é pouco confiável:** `reason_code` não tem associação detectável com os 452 feedbacks textuais de cancelamento (p = 0,955).

## 3. Por que CEO, Product e CS discordam

| Área | Afirmação | O que os dados mostram |
|---|---|---|
| CEO | "O churn aumentou" | Os eventos registrados sobem, mas não estabelecem maior propensão de perda. Três sinais de churn incompatíveis |
| Product | "O uso aumentou" | O uso total fica estável (30.789–32.227 por trimestre). O uso por conta ativa* **caiu em 15 de 15 segmentos** (−40% a −77%), porque a base cresceu |
| CS | "A satisfação está saudável" | 41,25% dos tickets sem resposta de CSAT; notas observadas só entre 3 e 5; sem relação com churn nem com a operação de suporte |

\* Uso por conta ativa = soma de `usage_count` no período ÷ nº de contas com ≥ 1 registro de assinatura ativo na data de fim do período.

**As três áreas usam métricas com grãos e denominadores incompatíveis. Nenhuma delas mede a saúde do cliente.**

| O que sabemos | O que não sabemos |
|---|---|
| Os sinais de churn discordam (110 / 352 / 312; checagem de estado = 0) | Por que um cliente individual realmente sai |
| A qualidade temporal de uso e suporte é baixa | A data comercial real de renovação |
| `reason_code` é semanticamente inconsistente | A perda real no nível de contrato |
| Não há sinal preditivo robusto | O efeito causal de qualquer ação de retenção |
| Alguns segmentos têm taxa observada maior (não validada) | |
| As filas de ação são operacionalmente válidas | |

## 4. Quem o CS deve revisar primeiro

Não há segmento nem conta com risco de churn previsível; nenhuma diferença foi validada. As maiores taxas **observadas** de `churn_flag` estão em DevTools (35 / 113 = 31,0%) e no canal event (29 / 96 = 30,2%), contra 110 / 500 = 22,0% da média. A diferença não é robusta o bastante para direcionar investimento de retenção (q = 0,28): esses segmentos entram como **sobreamostra qualitativa nas entrevistas de saída** (OBSERVED — NOT VALIDATED AS HIGHER RISK).

A priorização abaixo é **de negócio, não de risco**:

| Fila | Regra | Contas | MRR proxy | Ação |
|---|---|---|---|---|
| **V1 Reconciliação de status** | `churn_flag` = true e MRR proxy ativo > 0 | 110 | 2.073.153 (20,4%) | RevOps confirma o status real em 14 dias |
| **V2 Cobertura de valor** | Top 50 por MRR proxy ativo | 50 | 2.781.650 (27,4%) | Dono, comprador econômico, champion, data de renovação, revisão de valor |
| **V3 Prontidão de renovação manual** | Registros ativos sem auto-renew e com MRR proxy > 0 | 388 | 2.023.778 (19,9%) | Capturar data de renovação e dono, começando pela onda V3-W1 (top 50 por exposição: 873.996; 43,2% da V3) |

**Onda dos primeiros 30 dias = V1 ∪ V2 ∪ V3-W1 = 176 contas únicas.** Não são 210: V1∩V2 = 9, V1∩V3-W1 = 11, V2∩V3-W1 = 17, nas três = 3. Lista nominal em `RavenStack_CS_Action_Queues.xlsx`.

*Na V3: das 409 contas com algum registro ativo `auto_renew = false`, 21 possuem somente exposições `auto_renew = false` de trial com MRR proxy zero (elas têm outras assinaturas pagas ativas). Excluindo essas exposições sem valor econômico, restam 388 contas e 764 registros com MRR proxy positivo, totalizando 2.023.778.*

## 5. Exposição econômica

| Nível | Conteúdo |
|---|---|
| **1. Fato** | Exposição de renovação manual V3 = **2.023.778 de MRR proxy**; V3-W1 = 873.996; cobertura V2 = 2.781.650 |
| **2. Cenário condicional** | Se uma intervenção preservar, no fim, 5%, 10% ou 15% da exposição de renovação manual, o valor associado seria de **101.189, 202.378 ou 303.567 de MRR proxy por mês** (1.214.267, 2.428.534 ou 3.642.800 anualizados). *Cenário, não previsão. Nenhuma probabilidade é atribuída e não existe estimativa causal.* |
| **3. Efeito real** | Só pode ser medido pelo piloto controlado (seção 7) |

Os 1.127.644 de MRR proxy das assinaturas encerradas em 2024 são **referência descritiva**, não "receita perdida".

## 6. O que fazer na segunda-feira

1. **Aprovar uma definição canônica de churn.** Logo churn = conta sem nenhuma linha recorrente ativa; contraction separada. Tirar o `churn_flag` do board.
2. **Reconciliar as 110 contas da V1 em 14 dias.** Cada conta recebe ACTIVE, CONTRACTION, CANCELLATION SCHEDULED, CHURNED, DATA ERROR ou NEEDS REVIEW, apenas quando verificável.
3. **Nomear dono para as 50 contas da V2** e registrar comprador econômico, champion e data de renovação.
4. **Capturar a data de renovação da V3-W1 por fonte interna** (contrato, billing), sem contato com o cliente antes do sorteio do piloto.
5. **Trocar os reason codes (ação orientada pelos dados).** Os códigos atuais se distribuem quase uniformemente (15–19% cada) e não têm coerência detectável com o feedback textual. Substituir por taxonomia revisada com motivo principal + fatores contribuintes, resposta aberta, fonte e confiança do motivo, e entrevistas de saída.
6. **Não construir agora:**
   - probabilidade de churn;
   - watchlist preditiva;
   - health score;
   - Revenue at Risk;
   - programa "Enterprise";
   - estratégia por país ou mercado;
   - filas de adoção ou de suporte com os dados atuais.

## 7. 30 / 60 / 90 dias

| Janela | Foco | Entregas |
|---|---|---|
| **0–30: verdade + triagem** | Parar de medir errado | Definição canônica; V1 reconciliada; donos da V2; datas da V3-W1; pesquisa de saída v2; Churn Truth Lab |
| **31–60: lifecycle** | Tornar churn mensurável | `contract_id`, `product_id`, predecessor, `renewal_due_date`, datas de pedido e de efetivação do cancelamento; classificação mensal de movimentos; rotina de renovação; entrevistas de saída |
| **61–90: lançamento do piloto** | Medir o que funciona | População sem contaminação (V3 − V2 − V3-W1 = **314 contas**, 157 por braço), pré-registro, sorteio, início do outreach de renovação; redesenho da telemetria de adoção; KPIs de retenção v1 |

**O piloto não terá resultado em 90 dias.** Os 90 dias são a janela de lançamento, e a leitura ocorre quando um número pré-registrado de contratos tiver vencido. O resultado principal é renovar ou não no vencimento; o secundário é o MRR proxy retido e a contraction.

Com taxas de não renovação **hipotéticas** de 10%, 15% ou 20%, o desenho tem cerca de 80% de poder apenas para efeitos absolutos de ~7,4, 9,4 ou 11,0 pontos percentuais.
