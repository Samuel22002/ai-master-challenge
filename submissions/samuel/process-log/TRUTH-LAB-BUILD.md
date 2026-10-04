# TRUTH-LAB-BUILD-02 — Process Log

> **Nota de empacotamento (FINAL-SUBMISSION-PACKAGE-01).** Este documento foi copiado do workspace de desenvolvimento sem alterar evidência. Os scripts citados estão em `solution/scripts/` e os outputs em `solution/outputs/`. Documentos de ciclos de desenvolvimento citados como fonte (ANALYSIS-08 a 16, AUDIT-01, docs numerados 09–21, `solution/outputs/environment_rerun/`) ficaram no workspace e não fazem parte do pacote; o que eles sustentam está consolidado aqui, no apêndice técnico e nos outputs incluídos.

Data: 2026-10-04 · Ferramenta: Antigravity IDE / Claude Code (extensão `anthropic.claude-code` 2.1.289) — host verificado no ambiente (`claude.exe` da extensão, processo-filho do `Antigravity IDE.exe`) · Resultado da construção: **TRUTH LAB READY FOR HUMAN REVIEW** → depois do fechamento (seção final): **READY FOR FINAL INDEPENDENT AUDIT**.

## Prompt recebido

Samuel pediu a construção do RavenStack Churn Truth Lab como aplicação estática, sobre a fonte de verdade já validada.

Requisitos:
- HTML, CSS e JavaScript puros;
- abrir a partir de `index.html`, sem servidor, backend, API, internet ou CDN;
- seis telas;
- SOURCE / GRAIN / COVERAGE / LIMITATION em todo número;
- rótulos globais obrigatórios;
- lista de frases proibidas;
- dados pré-calculados em Python;
- testes automáticos numéricos, de frases proibidas, offline e funcionais;
- process log e doc de validação.

Restrições: nada de nova análise, modelo, score, probabilidade ou alteração de número validado. Em caso de conflito com a fonte de verdade, parar e reportar.

## Arquivos lidos

- `docs/FINAL-EVIDENCE-REGISTER.md` (F-01 a F-22, incluindo o F-16 corrigido);
- `README.md`, `solution/EXECUTIVE-DIAGNOSIS.md`, `docs/TECHNICAL-APPENDIX.md`, `docs/TRUTH-LAB-REQUIREMENTS.md`;
- `docs/21-auditor-integration-validation.md`;
- `solution/outputs/final_rewrite/final_numbers.json` e `segment_usage_per_active_account.csv`;
- `solution/outputs/auditor_integration/`: resumo, segmentos, flags por conta, definição do denominador;
- `solution/outputs/end_to_end_sweep/quarterly_claims.csv`;
- `solution/scripts/final_rewrite_build.py` e `solution/scripts/end_to_end_sweep.py`, para as regras de fila e de conta ativa.

## Conflitos verificados antes de construir

Não encontrei conflito entre a UI pedida e a fonte de verdade. Encontrei dois conflitos **internos ao próprio prompt**, resolvidos com regras declaradas e não por escolha silenciosa:

1. **O rótulo obrigatório "Business priority — not predicted churn risk" contém a frase proibida "predicted churn risk".** Regra: os testes de frases proibidas excluem apenas esse rótulo negado, listado explicitamente; qualquer outra ocorrência falha.
2. **A dimensão obrigatória "Revenue history" contém a palavra "revenue"**, que o F-16 proíbe como rótulo de MRR. Regra: "revenue" só é aceito no rótulo "MRR proxy — not consolidated revenue" e no nome dessa dimensão, que descreve a falta de histórico de receita, sem chamar o MRR de receita.

## Decisões de implementação

- **Dados pré-calculados.** `solution/scripts/build_truth_lab_data.py` lê os números de `final_numbers.json` e `auditor_integration_summary.json`. O detalhe por conta e por trimestre vem dos CSVs brutos, com as mesmas regras dos scripts validados. Antes de gravar, o script verifica:
  - filas, totais e onda iguais ao `final_numbers.json`;
  - série trimestral igual ao `quarterly_claims.csv`;
  - flags iguais ao resumo do auditor;
  - simulador igual aos cenários validados.
- **JSON + cópia em `.js`.** Uma página aberta de `file://` não consegue `fetch()` de JSON, então a página carrega `truth_lab_data.js` (`window.TRUTH_LAB_DATA`). O verificador garante que os dois arquivos são idênticos.
- **O navegador não recalcula números analíticos.** O simulador consulta uma tabela pré-calculada de 0 a 20%. A única conta feita no navegador é o break-even (custo informado pelo usuário ÷ 2.023.778), como o prompt especifica.
- **Gráficos em SVG desenhados à mão,** sem biblioteca: UpSet plot para as definições (evitando Venn), small multiples para o denominador, barras divergentes para os 15 segmentos e forest plot com IC de Wilson para as taxas observadas. Fontes do sistema, sem fonte externa.
- **Metadados.** Cada número tem um **i** que abre um painel lateral com SOURCE / GRAIN / COVERAGE / LIMITATION, lido do JSON. Gráficos, tabela e seções do brief também têm ficha.
- **Denominador.** O tooltip de todo ponto dos gráficos de uso mostra a "DENOMINATOR DEFINITION" lida de `usage_denominator_definition.json`.
- **V1.** Os seis estados de revisão aparecem como seletor por conta, vazios por padrão, e são exportados no CSV.
- **CSM prep.** As seis perguntas são fixas. A sexta indica "n/a" quando a conta não tem registro ativo sem auto-renew.
- **Idioma.** Headline, subheadline e causa de gestão usam o texto em português dado no prompt; os demais rótulos seguem o inglês do prompt.

## Problemas encontrados e correções

| Problema | Como apareceu | Correção |
|---|---|---|
| A reexecução da ANALYSIS-15, deixada em segundo plano na etapa anterior, aparecia como "failed" | Notificação da tarefa | O pipeline tinha terminado (22 min); quem falhou foi o `tail` no fim do comando. Comparação feita: 54/54 células idênticas aos outputs anteriores |
| Valor esperado "~11 pp" no autoteste | Revisão antes de rodar | O JSON exibe "~11.0 pp", igual à fonte; o teste foi corrigido |
| 10 defeitos visuais (quebras de linha em "157 / 157" e "418 / 500", rótulos sobrepostos na barra de concentração, IC minúsculo no forest plot, '24Q4 cortado, "α" virando "A" em caixa alta, número colado na barra do UpSet, pills empilhadas no brief, card V1 esticado) | Screenshots headless de cada tela, revisados um a um | CSS e geometria corrigidos; novas screenshots conferidas |
| Eixo "1k" para 1.495 | Screenshot | Rótulo passou a "1.5k" |
| A varredura de moeda acusou "0 $" no `app.js` | Primeira execução do verificador | Falso positivo: sintaxe `${…}` de template do JavaScript. O verificador ignora `${` em `.js`; o texto renderizado continua varrido pelo autoteste |
| A checagem "sem requests externos" do autoteste via 0 recursos | Leitura do resultado | `file://` não aparece na API de recursos do navegador, então a checagem prova pouco. Foram acrescentados uma varredura estática de URLs e o autoteste rodando com a rede **desligada** no navegador |

## Testes

`solution/scripts/check_truth_lab.py` na construção → **205/205 PASS** (no fechamento, com 8 checagens novas de wording: **213/213**):

| Grupo | Resultado | O que cobre |
|---|---|---|
| Numéricos | 78/78 | Todos os números do prompt contra o JSON e os outputs validados |
| Metadados | 1/1 | 67 métricas com as 4 fichas |
| Frases proibidas | 12/12 | 6 arquivos |
| Moeda | 6/6 | 6 arquivos |
| Offline (estático) | 6/6 | 6 arquivos |
| Arquivos | 8/8 | Árvore de arquivos |
| Funcionais | 94/94 | Autoteste no Edge headless, de `file://`, com a rede desligada: 6 telas, filtros, busca, ordenação, brief, CSV, simulador, break-even, painel de metadados, frases proibidas no texto renderizado, zero erros de janela e de console |

Teste negativo do próprio verificador: frases proibidas, moeda e referência externa injetadas foram detectadas.

## Status final

Construção: **TRUTH LAB READY FOR HUMAN REVIEW**. Ver o fechamento abaixo.

## Revisão humana e fechamento (FINAL-CLOSEOUT-TRUTH-LAB-01)

**Revisão humana (Samuel).** Aprovou a estrutura do brief da conta, das filas de ação, do denominador e da confiança dos dados, e pediu para não redesenhar. Apontou:
- mistura excessiva de português e inglês;
- "unsafe" e "at stake" mais dramáticos que a evidência.

**Auditor.** Apontou que 110 / 352 / 312 / 0 não são "quatro definições": são três sinais de churn e uma checagem de estado observável.

**Correções finais de wording (sem mudar layout nem números):**

| Antes | Depois |
|---|---|
| "Four definitions. Four different answers." | "Três sinais de churn + uma checagem de estado observável." / "Quatro respostas diferentes." |
| "Why prediction is unsafe today" | "Por que uma previsão não é suportada hoje" |
| "What is at stake in manual renewals" | "O que a exposição de renovação manual pode representar" |
| Card de outcome: "110 / 352 / 312 / 0 — four definitions" | "110 / 352 / 312 = três populações de churn conflitantes. 0 = checagem do estado observável no fim." + LIMITATION "No reconciled customer-loss target" |
| Dimensão "Revenue history" | "Histórico financeiro" (mesmo nome do item A5; tira a palavra "revenue" da UI fora do rótulo obrigatório) |
| Interface com idiomas misturados | Interface em português, números em pt-BR; rótulos canônicos mantidos em inglês |

Também entraram:
- a fórmula do F-22 dentro do card "Uso / conta ativa";
- o parâmetro `?meta=` para abrir o painel de metadados pela URL (screenshot 07);
- 8 checagens novas de wording no autoteste;
- frases proibidas em português nos dois verificadores.

**Problemas encontrados no fechamento:**
- Dois falsos positivos na varredura do próprio código do teste: o nome de um caso de teste e a função de varredura. Foram resolvidos com regra declarada.
- Escapes em patches via shell quebraram strings do verificador duas vezes. A correção foi feita com a ferramenta de edição, e o verificador foi reexecutado.

**Testes finais:**
- `check_truth_lab.py` 213/213;
- autoteste no Chrome com a rede desligada: 101/101;
- `closeout_check.py`: 0 MUST FIX;
- checagens anteriores 55/55 e 40/40.

Detalhes em `docs/TRUTH-LAB-VALIDATION.md`.

**Reexecução dos modelos (status correto):** a ANALYSIS-15 terminou. A "falha" aparente veio de um comando no fim do script, não da execução dos modelos. Os 15 modelos saíram idênticos (54/54 valores).

**Status final:** READY FOR FINAL INDEPENDENT AUDIT. O QA manual de Samuel no navegador continua como confirmação humana; o checklist está no doc 23.
