# Validação do Churn Truth Lab

Consolida os relatórios de validação da construção e do fechamento do Truth Lab (docs 22 e 23 do workspace de desenvolvimento). A validação final da cópia empacotada está na Parte C.

> **Nota de empacotamento (FINAL-SUBMISSION-PACKAGE-01).** Este documento foi copiado do workspace de desenvolvimento sem alterar evidência. Os scripts citados estão em `solution/scripts/` e os outputs em `solution/outputs/`. Documentos de ciclos de desenvolvimento citados como fonte (ANALYSIS-08 a 16, AUDIT-01, docs numerados 09–21, `solution/outputs/environment_rerun/`) ficaram no workspace e não fazem parte do pacote; o que eles sustentam está consolidado aqui, no apêndice técnico e nos outputs incluídos.

## Parte A — Validação da construção (TRUTH-LAB-BUILD-02)

Data: 2026-10-04 · Decisão na construção: **TRUTH LAB READY FOR HUMAN REVIEW** · Após o fechamento: **READY FOR FINAL INDEPENDENT AUDIT** (`docs/TRUTH-LAB-VALIDATION.md`)

### Pacote de evidências (estado atual, após FINAL-CLOSEOUT-TRUTH-LAB-01)

| Teste | Resultado |
|---|---|
| Numéricos | **78/78** |
| Funcionais (autoteste no Edge headless, `file://`, rede desligada) | **102/102**: 94 da construção + 8 checagens de wording do fechamento |
| Frases proibidas / moeda (6 arquivos, inclusive equivalentes em português) | **PASS** (12/12 e 6/6) |
| Offline (estático + execução com a rede desligada) | **PASS** |
| Metadados / árvore de arquivos | **PASS** (1/1 e 8/8) |
| **TOTAL** | **213/213** (205 na construção; +8 no fechamento) |
| Navegadores | **Edge** validado (todos os testes); **Chrome** validado (autoteste 101/101 com a rede desligada) |

Limitações declaradas:
- desktop-first;
- mobile não testado formalmente;
- o estado de revisão V1 não persiste ao recarregar (sai pelo CSV);
- Edge e Chrome testados; Firefox e Safari não testados formalmente.

Interface agora em português, com números em pt-BR. As seções abaixo descrevem a validação da construção; os valores citados nelas em formato inglês foram exibidos em pt-BR a partir do fechamento.

> **HISTÓRICO / SUPERSEDED:** as seções 1 a 7 abaixo documentam o estado durante a construção. O estado final validado está nas Partes B e C.

Comando: `python solution/scripts/check_truth_lab.py` → **205/205 PASS**. Saídas em `solution/outputs/truth_lab/`:
- `truth_lab_checks.csv`;
- `selftest_dom_results.txt`;
- `screenshots/`.

### 1. Métricas verificadas (78/78)

Cada valor do JSON da UI foi conferido contra `final_numbers.json`, `auditor_integration_summary.json` e os valores literais do prompt:

| Grupo | Valores |
|---|---|
| Definições | 110 · 352 · 312 · 0; sobreposições 75 · 72 · 227 · 50 |
| Filas | V1 = 110 · 2.073.153 · 20,4%; V2 = 50 · 2.781.650 · 27,4%; V3 = 388 · 764 · 2.023.778 · 19,9%; V3-W1 = 50 · 137 · 873.996 · 43,2%; onda 176 (9 / 11 / 17 / 3) |
| V3 bruto | 409 contas · 899 registros; 21 com exposição de valor zero; 388 econômicas |
| Concentração | Top 10 = 8,4% · Top 20 = 14,3% · Top 50 = 27,4% |
| Piloto | 314 elegíveis · 157 / 157; MDE ~7,4 / ~9,4 / ~11,0 pp |
| Qualidade de dados | 5.568 / 25.000 · 13.198 / 25.000 · 1.077 / 2.000; 452 feedbacks; p = 0,955 |
| Semântica | 486 churn flags = 486 end_dates; 418 / 500 contas com os três planos; 9,0 registros ativos por conta |
| Segmentos | 35/113 · 29/96 · 29/109 · 25/97 · 33/134 (N ≥ 30); 110/500; Alemanha 8/25 excluída |
| Simulador | 5% = 101.189 / 1.214.267; 10% = 202.378 / 2.428.534; 15% = 303.567 / 3.642.800 |
| Health score | 0 GREEN · 2 PARTIAL · 8 RED |
| Dados por conta | 500 contas; somas por fila iguais aos totais validados; uso trimestral 30.789–32.227 |

Além disso, `build_truth_lab_data.py` aborta se qualquer agregado derivado dos CSVs brutos divergir dos outputs validados.

### 2. Testes funcionais (94/94)

Autoteste dentro da página (`index.html?selftest=1`), executado no Edge headless a partir de `file://`:

- as 6 telas renderizam; a headline está exata;
- painel de metadados: 67 ids, todos com SOURCE / GRAIN / COVERAGE / LIMITATION; o painel abre;
- 52 números conferidos no texto renderizado;
- denominador: filtro ALL → INDUSTRY → DevTools troca a série; 3 gráficos × 8 pontos; botão "ALL N ≥ 30" mostra 27 segmentos; Alemanha fora do ranking;
- tabela: filtros V1 = 110, V2 = 50, V3 = 388, V3-W1 = 50, WAVE 1 = 176; busca; ordenação por MRR e por coluna; CSV com cabeçalho + 110 linhas; estados V1 vazios;
- brief: abre por id e pela busca; 5 flags; 6 perguntas;
- simulador: 0%, 5%, 10% e 15% exatos; break-even vazio por padrão; 50.000 → 2,47%; aviso permanente;
- confiança: 10 dimensões; 0/2/8;
- frases proibidas e moeda no texto renderizado: nenhuma;
- zero erros de janela e zero erros de console.

### 3. Varredura de frases proibidas e moeda

Arquivos: `index.html`, `app.css`, `app.js`, `truth_lab_data.json`, `truth_lab_data.js`, `README.md`.

- Lista: high churn risk, predicted churn risk, predicted risk, churn probability, likelihood to churn, likely to churn, revenue at risk, expected loss, expected savings, still paying, "real churn = 0", zero customers churned, risk score.
- Moeda: R$, US$, BRL, USD, `$` junto de número.
- Resultado: **0 ocorrências.**
- Exceções declaradas (conflitos internos do prompt):
  - o rótulo obrigatório "Business priority — not predicted churn risk";
  - "revenue" só dentro de "MRR proxy — not consolidated revenue" e no nome da dimensão obrigatória "Revenue history".
- Teste negativo: frases, moeda e URL injetadas foram detectadas pelo verificador.

### 4. Teste offline

- **Estático:** nenhuma URL `http(s)`, `//`, `@import` ou CDN nos arquivos entregues. A única string `http` é o namespace XML do SVG, que não é request.
- **Dinâmico:** o autoteste roda com a rede desligada no navegador (`--host-resolver-rules=MAP * ~NOTFOUND`, `--proxy-server=127.0.0.1:9`) e passa em 94/94.
- Sem servidor, backend ou API: a página abre por `file://`.

### 5. Arquivos

```
solution/truth-lab/
├── index.html
├── README.md
├── assets/css/app.css
├── assets/js/app.js
└── data/truth_lab_data.json · truth_lab_data.js   (1,2 MB cada)
solution/scripts/build_truth_lab_data.py
solution/scripts/check_truth_lab.py
solution/outputs/truth_lab/ (truth_lab_checks.csv, selftest_dom_results.txt — gerados por check_truth_lab.py)
process-log/TRUTH-LAB-BUILD.md
```

### 6. Limitações

- **Desktop-first.** Há um breakpoint em 1.100 px, mas não foi testado em celular.
- **A tabela de filas** tem 11 colunas; em telas menores que ~1.600 px as últimas exigem rolagem horizontal.
- **Os estados de revisão V1** ficam só na memória da página (não persistem ao recarregar); saem pelo CSV.
- **Testado só em Edge (Chromium)** na construção. No fechamento, o Chrome também foi validado (Parte B). Firefox e Safari não foram testados.
- **A checagem de recursos do autoteste** não enxerga arquivos `file://`. O offline é provado pela varredura estática e pela execução com a rede desligada.
- **Fontes do sistema** (Segoe UI no Windows): a aparência muda um pouco em outros sistemas.
- **Idioma misto** na construção: headline, subheadline e causa de gestão em português (texto do prompt); o restante em inglês. No fechamento, a interface inteira passou para o português (Parte B).

### 7. Screenshots planejadas na construção

> **HISTÓRICO / SUPERSEDED:** lista planejada durante a construção. As screenshots finais (01 a 07) estão em `process-log/screenshots/truth-lab/` e são descritas na Parte B §9.

Plano da construção:

1. Churn Truth: headline, três sinais de churn + uma checagem de estado observável, e UpSet.
2. Painel lateral aberto num número (ex.: 2.023.778) mostrando SOURCE / GRAIN / COVERAGE / LIMITATION.
3. Denominator com filtro INDUSTRY → DevTools e o tooltip da definição do denominador.
4. Ranking de segmentos com o rótulo "Observed — not validated as higher risk".
5. Action Queues: os três blocos, a onda 176 e a tabela filtrada em V1.
6. Account Brief de uma conta da onda 1.
7. Impact Lab com o slider em 10% e o aviso permanente.
8. Data Confidence: matriz e readiness 0/2/8.


## Parte B — Fechamento (FINAL-CLOSEOUT-TRUTH-LAB-01 e FINAL-README-SYNC-01)

Data: 2026-10-04 · Decisão: **READY FOR FINAL INDEPENDENT AUDIT**

Escopo: só wording, consistência, sincronização de documentos e QA. Nenhuma análise nova, nenhum número validado alterado, nenhum redesenho.

### 1. Correções aplicadas

| # | Item | Correção |
|---|---|---|
| 1 | "Four definitions" | Tornou-se "Três sinais de churn + uma checagem de estado observável" / "Quatro respostas diferentes" no Truth Lab, no README, no diagnóstico executivo, no apêndice, na especificação e nos process logs |
| 2 | Card de outcome (Data Confidence) | "110 / 352 / 312 = três populações de churn conflitantes. 0 = checagem do estado observável no fim." · RED · LIMITATION "No reconciled customer-loss target" |
| 3 | "Still paying" | Nenhuma ocorrência atual. O README e o diagnóstico usam "ainda possuem registros de subscription ativos com MRR proxy positivo" |
| 4–5 | Headline e causa raiz em dois níveis | Mantidas literalmente |
| 6 | F-18 a F-22 no README | Linhas já presentes (22,27%; 52,8%; 53,9%; suporte sem separação; p = 0,955), mais uma frase sobre a semântica das assinaturas (~9,0 registros por conta; 418 / 500) |
| 7 | Denominador F-22 visível | Fórmula no card "Uso / conta ativa", na nota da página, no tooltip e na ficha do Truth Lab; também no README (nota ¹), no diagnóstico executivo (nota \*) e no apêndice (A2g). Mesma regra em todos |
| 8 | Range de AUC antigo | Removido do conteúdo atual. README: "não superaram de forma robusta seus respectivos nulls". Apêndice e registro com os valores exatos (ver conflito abaixo) |
| 9–10 | Status do Truth Lab | "Construído e validado" no README da submissão, na especificação, no README da raiz e no CLAUDE.md/AGENTS.md. Investigation CLOSED · Truth Lab BUILT / FINAL QA · Next stage FINAL AUDIT + SUBMISSION PACKAGING |
| 11 | Idioma da UI | Português predominante, números em pt-BR (só formatação). Rótulos canônicos em inglês: labels globais, SOURCE/GRAIN/COVERAGE/LIMITATION, RED/PARTIAL/WARNING, NOT IDENTIFIABLE, termos de campo |
| 12 | "Unsafe" | "Por que uma previsão não é suportada hoje" |
| 13–14 | "At stake" / revenue | "O que a exposição de renovação manual pode representar". "Revenue" só no rótulo obrigatório; "Revenue history" virou "Histórico financeiro" |
| 19 | Placeholders do process log | ChatGPT/OpenAI registrado como confirmado por Samuel (prompts, metodologia, red-team, aderência ao challenge, enquadramento de soluções, especificação do Truth Lab). ANALYSIS-16: "tool attribution not independently verified". LinkedIn continua como campo de Samuel (não pode ser inventado) |
| 20–21 | Process log do Truth Lab e status da reexecução | Seção de revisão humana e fechamento acrescentada. A reexecução da ANALYSIS-15 foi concluída: a falha aparente veio de um comando no fim do script; 15 modelos idênticos, 54/54 valores |
| 23 | `.env` | Não versionado (ver seção 7) |

**Conflito registrado (item 8).** O prompt dá o range validado como ~0,449–0,515. Esse é só o intervalo dos 6 modelos da ANALYSIS-15. Os 9 modelos da ANALYSIS-14, reproduzidos idênticos, vão de 0,454 a 0,538. Adotei os valores exatos dos dois conjuntos (0,449–0,538 no total) em vez de aplicar 0,515 aos 15 modelos. No registro (F-09), "0,45 a 0,54" virou "0,454 a 0,538" (só precisão; o achado não muda).

### 2. Críticas do auditor resolvidas

"Four definitions" → três sinais + uma checagem · card de outcome · "still paying" · F-18 a F-22 no README · F-22 ao lado da métrica · AUC antigo · status "não construído" · placeholders do process log · status da reexecução dos modelos.

### 3. Ajustes da revisão humana

- Interface coerente em português.
- "Unsafe" e "at stake" substituídos.
- Brief, filas, denominador e confiança dos dados sem redesenho; só textos.
- Screenshot 07 com o painel de metadados aberto (parâmetro `?meta=`).

### 4. Arquivos alterados

- **Truth Lab:** `index.html`, `assets/js/app.js`, `assets/css/app.css` (dois estilos de texto), `data/truth_lab_data.json` e `.js` (regerados), `README.md`.
- **Scripts:**
  - `solution/scripts/build_truth_lab_data.py` (textos em PT, pt-BR, ficha `conf_outcome`);
  - `solution/scripts/check_truth_lab.py` (pt-BR, frases em PT, wording antigo);
  - `solution/scripts/closeout_check.py` (novo);
  - `solution/scripts/final_rewrite_check.py` e `solution/scripts/auditor_integration_check.py` (doc 22 fora da varredura; N10 com 3 casas).
- **Submissão:** `README.md`, `solution/EXECUTIVE-DIAGNOSIS.md`, `docs/TECHNICAL-APPENDIX.md`, `docs/TRUTH-LAB-REQUIREMENTS.md`, `process-log/PROCESS-LOG.md`, `process-log/TRUTH-LAB-BUILD.md`, `process-log/screenshots/truth-lab/` (7 PNGs finais).
- **Workspace:** `README.md` (raiz), `CLAUDE.md`, `AGENTS.md`, `docs/FINAL-EVIDENCE-REGISTER.md` (precisão do AUC no F-09), `docs/TRUTH-LAB-VALIDATION.md`, este doc.

### 5. Fonte de verdade atual

RAW DATA > outputs reproduzíveis > scripts validados > `docs/FINAL-EVIDENCE-REGISTER.md` (F-01 a F-22) > `README.md` > diagnóstico executivo > Truth Lab > históricos.

**Congelado e conferido:**
- 110 / 352 / 312 / 0; sobreposições 75 / 72 / 227 / 50;
- V1 110 · V2 50 · V3 388 / 764 / 2.023.778 · V3-W1 50 / 137 / 873.996 · onda 176;
- F-18 a F-22;
- piloto 314 = 157 + 157; MDE ~7,4 / 9,4 / 11,0 pp.

**Consistência entre documentos atuais:** os números acima batem entre o registro, os READMEs, o CLAUDE/AGENTS, o diagnóstico, o apêndice, a especificação, a UI e os docs 22/23 (checado por `final_rewrite_check.py`, `auditor_integration_check.py` e `check_truth_lab.py`). Não há divergência material.

### 6. Resultados dos testes

| Verificação | Resultado |
|---|---|
| `build_truth_lab_data.py` (checagens contra os outputs validados) | OK |
| `check_truth_lab.py` | **213/213**: numéricos 78; metadados 1; frases proibidas 12; moeda 6; offline 6; arquivos 8; funcionais 102 |
| `closeout_check.py` (item 27, conteúdo atual) | **0 MUST FIX** (74 CURRENT CORRECT, 3 HISTORICAL; 16 arquivos); testes negativos confirmam que pega cada padrão |
| `final_rewrite_check.py` | 55/55 afirmações; varredura sem MUST FIX |
| `auditor_integration_check.py` | 40/40 afirmações; varredura sem MUST FIX |

### 7. Segurança do `.env`

- `git check-ignore -v .env` → `bases/g4-ai-master-challenge-churn/.gitignore:1:.env`.
- `git ls-files --error-unmatch .env` → não rastreado.
- `.env.example` pode permanecer.
- O conteúdo do `.env` não foi lido nem exibido.

### 8. QA no navegador

**Automatizado (feito por mim), em Edge e Chrome reais em modo headless, abrindo `index.html` por `file://`:**
- as 6 páginas e a navegação;
- busca de conta; filtro V1 (110); ordenação; brief da conta;
- exportação CSV (cabeçalho + 110 linhas);
- simulador em 5/10/15% e o campo de custo hipotético (50.000 → 2,47%);
- painel de metadados;
- zero erros de janela e de console;
- rede desligada.

Cada execução é um carregamento novo: houve 9 carregamentos limpos nesta etapa (7 screenshots e 2 autotestes).

**Manual (Samuel), checklist de 5 minutos:**
1. Abrir `index.html` com dois cliques.
2. Passar pelas 6 telas.
3. Buscar `A-30b4ca` no brief.
4. Filtrar V1 e ordenar por MRR.
5. Exportar o CSV.
6. Pôr o slider em 10% (202.378 / 2.428.534).
7. Digitar um custo.
8. Clicar num **i**.
9. Recarregar com F5.
10. Abrir o console (F12) e conferir que não há erros.

Eu não executo cliques manuais. Essa confirmação humana continua com Samuel e não bloqueia a auditoria.

### 9. Screenshots

`process-log/screenshots/truth-lab/`, capturadas no Edge (Chromium) a 1440 px de largura:

- 01 Verdade do churn;
- 02 Denominador + segmentos observados;
- 03 Filas de ação;
- 04 Brief da conta (A-30b4ca);
- 05 Lab de impacto;
- 06 Confiança dos dados;
- 07 Painel de metadados aberto (SOURCE / GRAIN / COVERAGE / LIMITATION de 2.023.778).

### 10. Limitações restantes

- Desktop-first; mobile não testado formalmente; a tabela de filas rola na horizontal abaixo de ~1.600 px.
- O estado de revisão V1 não persiste ao recarregar (sai pelo CSV).
- Edge e Chrome testados; Firefox e Safari não.
- Fontes do sistema: a aparência pode mudar um pouco em outros sistemas.

### 11. Estado atual da submissão

*Atualizado após a abertura do PR. A versão anterior desta seção listava LinkedIn, exports das conversas e empacotamento dos scripts como pendências; todas foram resolvidas assim:*

- LinkedIn preenchido no `README.md`.
- Formato principal do Process Log: narrativa escrita. Screenshots e exports de conversas não são o formato escolhido.
- Scripts em `solution/scripts/` e outputs em `solution/outputs/`, dentro do pacote `submissions/samuel/`.
- PR #177 aberto no repositório oficial, com 104 arquivos, todos dentro de `submissions/samuel/`.
- O checklist manual de 5 minutos (§8) continua sob responsabilidade de Samuel.

### 12. Final executive wording cleanup (FINAL-README-SYNC-01)

Só redação e atribuição; nenhum número alterado.

**As 5 correções:**

| # | Antes | Depois | Onde |
|---|---|---|---|
| 1 | "O CEO reage a um número que não mede perda de cliente. Product e CS olham métricas sem denominador ou que não medem nada." | "O CEO reage a indicadores que não podem ser interpretados de forma confiável como perda de cliente. Product e CS observam métricas que, isoladamente, não permitem inferir retenção ou saúde do cliente." | README da submissão (Em 2 minutos) |
| 2 | "Isso não significa ausência de perda: significa que os registros não permitem enxergar a perda." | "Isso não significa ausência de perda real: significa que o estado contratual observável não permite identificar de forma confiável perda completa da conta." | README; diagnóstico executivo (variante "enxergá-la"); LIMITATION da ficha `def_zero` do Truth Lab |
| 3 | reason_code × feedback com "p = 0,95" | "p = 0,955" | README; diagnóstico executivo. O registro, o apêndice, o Truth Lab e os docs do auditor já usavam 0,955 |
| 4 | "Enterprise não serve como segmento de risco; o que importa é o valor da conta." | "…; para priorização operacional imediata, a concentração de valor é mais útil." | README da submissão |
| 5 | Truth Lab e trabalho desta sessão atribuídos a "Claude Code" | "Antigravity IDE / Claude Code (extensão `anthropic.claude-code` 2.1.289)" | Tabelas de ferramentas do README e do PROCESS-LOG; cabeçalho do TRUTH-LAB-BUILD |

**Atribuição de ferramentas (final).**
- A evidência veio do ambiente, não de suposição:
  - a cadeia de processos dos comandos desta sessão é `powershell.exe ← cmd.exe ← claude.exe ← Antigravity IDE.exe`;
  - o `claude.exe` está em `.antigravity-ide\extensions\anthropic.claude-code-2.1.289-win32-x64\`;
  - `CLAUDE_CODE_ENTRYPOINT=claude-vscode`.
- Conclusão: a extensão Claude Code rodando dentro do Antigravity IDE, registrada como "Antigravity IDE / Claude Code".
- ChatGPT / OpenAI continua confirmado por Samuel (prompts, metodologia, red-team, aderência ao challenge, enquadramento de soluções, especificação do Truth Lab).
- ANALYSIS-16: "tool attribution not independently verified".

**Arquivos afetados:**
- `README.md`, `solution/EXECUTIVE-DIAGNOSIS.md`, `process-log/PROCESS-LOG.md`, `process-log/TRUTH-LAB-BUILD.md`;
- `solution/scripts/build_truth_lab_data.py` e o JSON/JS do Truth Lab regerado (só o texto da ficha `def_zero`);
- `solution/scripts/auditor_integration_check.py` (N08 passou a esperar 0,955 com 3 casas);
- `solution/scripts/closeout_check.py` (padrões deste pedido; regra "antigo/antiga" restringida para não casar "Antigravity").

**Varredura de frases antigas:**
- `closeout_check.py`: **0 MUST FIX** (78 CURRENT CORRECT, 3 HISTORICAL, incluindo as linhas "antes → depois" desta seção).
- Testes negativos: as 6 frases antigas deste pedido e as 8 do item 27 são detectadas; as versões corretas não são.

**Testes:**
- `check_truth_lab.py` 213/213;
- `final_rewrite_check.py` 55/55, sem MUST FIX;
- `auditor_integration_check.py` 40/40, sem MUST FIX;
- links relativos da submissão: 6/6 válidos.

**Regressão numérica:**
- `final_numbers.json` idêntico;
- no JSON do Truth Lab, todos os 68 valores e textos de exibição são idênticos; só mudou a LIMITATION de `def_zero`;
- contas, séries, segmentos, simulador e confiança idênticos.

## Parte C — Validação da cópia empacotada (FINAL-SUBMISSION-PACKAGE-01)

Todos os testes desta parte rodaram sobre a cópia final em `submissions/samuel/`, já dentro do clone do fork. Nenhum rodou só sobre a versão de desenvolvimento.

### 1. Testes na cópia final

| Script | Resultado |
|---|---|
| `check_truth_lab.py` | 213/213: numérico 78, metadados 1, frases proibidas 12, moeda 6, offline 6, arquivos 8, funcional 102. A parte funcional abriu `solution/truth-lab/index.html` por `file://` em navegador headless com a rede desligada |
| `final_rewrite_check.py` | 55/55 afirmações verificadas; 8/8 checagens da planilha |
| `auditor_integration_check.py` | 40/40 afirmações verificadas |
| `closeout_check.py` | 0 MUST FIX (76 corretas, 3 históricas) |
| `package_check.py` | 95/95: template, links, caminhos, arquivos, segredos, Truth Lab e escopo do PR |

### 2. Reprodução a partir dos dados brutos

Os passos 1 a 5 de `solution/README.md` foram reexecutados numa cópia limpa do pacote com os 5 CSVs do Kaggle (`RAVENSTACK_DATA`). Todos os arquivos que cada script regenera saíram byte a byte iguais aos enviados:

| Script | Arquivos comparados | Tempo |
|---|---|---|
| `final_rewrite_build.py` | `final_numbers.json` | ~7 s |
| `auditor_integration.py` | `auditor_integration_summary.json` | ~46 s |
| `independent_audit.py` (1.000 simulações) | 14 de 14 | 632 s |
| `end_to_end_sweep.py` | 17 de 17 | 649 s |
| `unblocked_models.py` | 6 de 6 regenerados (os outros 3 arquivos da pasta são insumos que o script não grava) | 1.133 s |

### 3. Escopo do PR

No clone do fork, na branch da submissão, `git add -n -f submissions/samuel` listou só arquivos dentro de `submissions/samuel/`, sem `.env`, `.pyc` nem `__pycache__`. Nenhum arquivo fora da pasta foi alterado.
