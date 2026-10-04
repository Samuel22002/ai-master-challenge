# RavenStack Churn Truth Lab

Página estática e offline que responde a duas perguntas:

- **CEO:** qual número de churn devo acreditar e qual é o problema real?
- **CS / RevOps:** quais contas revisar agora e por quê?

Ela não responde "quem vai churnar". Não tem previsão, score nem probabilidade.

**Status:** construído e validado — 205 testes automáticos, mais os que forem acrescentados (`solution/scripts/check_truth_lab.py`).

## Como abrir

Dois cliques em `index.html`. Não precisa de servidor, backend, API, internet nem CDN. As fontes são do sistema e os gráficos são SVG desenhados à mão.

## As seis telas

| Tela | O que mostra |
|---|---|
| 01 Verdade do churn | Três sinais de churn (110 / 352 / 312) e uma checagem de estado observável (0) — quatro respostas diferentes; UpSet plot da sobreposição; causa raiz de gestão separada da causa individual (NOT IDENTIFIABLE); "Por que uma previsão não é suportada hoje" (qualidade de dados, não causas) |
| 02 Denominador | Uso total, uso por conta ativa e uso por assinatura ativa por trimestre, com filtros de indústria, país e plano e a fórmula do F-22 ao lado da métrica; variação dos 15 segmentos; taxa observada de churn_flag por segmento (N ≥ 30, IC 95%, "Observed — not validated as higher risk") |
| 03 Filas de ação | V1 / V2 / V3-W1; a onda de 176 contas e as sobreposições; concentração e checklist da V2; a explicação 409 → 21 → 388 da V3; tabela com busca, ordenação, filtro, exportação CSV e estados de revisão V1 (nunca pré-preenchidos); roadmap 30/60/90 |
| 04 Brief da conta | Uma conta nas cinco tabelas: valor, lifecycle, produto, suporte, cinco flags descritivas de qualidade de dados, registros de assinatura, churn events e perguntas fixas para o CSM |
| 05 Lab de impacto | Controle de 0–20% sobre a exposição V3 de 2.023.778 de MRR proxy, custo hipotético opcional para break-even e o cartão do piloto. Aviso permanente: "Scenario — not forecast · No probability · No causal estimate" |
| 06 Confiança dos dados | Matriz de 10 dimensões, prontidão para health score (0 GREEN · 2 PARTIAL · 8 RED) e semântica das assinaturas |

Clique em qualquer **i** para ver SOURCE, GRAIN, COVERAGE e LIMITATION do número. Para abrir uma ficha direto pela URL: `index.html?meta=v3_mrr#queues`.

## Idioma e formato

- A interface é em português, com números no formato brasileiro (2.023.778; 22,27%). Só a formatação mudou; os valores são os mesmos.
- Os rótulos canônicos continuam em inglês: os labels globais ("MRR proxy — not consolidated revenue", "Business priority — not predicted churn risk", etc.), SOURCE / GRAIN / COVERAGE / LIMITATION, os status RED / PARTIAL / WARNING e NOT IDENTIFIABLE.

## Dados

- `data/truth_lab_data.json` traz todas as métricas já calculadas.
- `data/truth_lab_data.js` é o mesmo objeto como `window.TRUTH_LAB_DATA`, porque uma página aberta de `file://` não consegue `fetch()` de um JSON.
- Os dois arquivos são gerados por `solution/scripts/build_truth_lab_data.py`:
  - a partir dos outputs validados (`final_numbers.json`, `auditor_integration_summary.json`, `auditor_integration/*.csv`, `quarterly_claims.csv`);
  - e dos CSVs brutos, para o detalhe por conta e por trimestre.
- O gerador verifica cada agregado contra os valores validados antes de gravar.
- O navegador não recalcula nenhum número analítico. Ele só formata, desenha os gráficos e divide o custo hipotético informado pelo usuário.

Todos os valores são **MRR proxy**: o dataset não declara moeda para `mrr_amount`.

## Testes

`python solution/scripts/check_truth_lab.py` roda:

- testes numéricos contra os outputs validados;
- varredura de frases proibidas e de moeda;
- varredura offline (nenhuma referência externa);
- checagem da árvore de arquivos;
- o autoteste da página no Edge headless, a partir de `file://` e com a rede desligada.

Autoteste manual: abra `index.html?selftest=1`; o resultado aparece no fim da página.

<!-- forbidden-list -->
A lista de frases proibidas fica em `solution/scripts/check_truth_lab.py` e no autoteste em `assets/js/app.js`. A única exceção é o rótulo negado obrigatório "Business priority — not predicted churn risk".
<!-- /forbidden-list -->
