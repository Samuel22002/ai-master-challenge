# Como executar a solução

Todos os comandos abaixo partem da pasta `submissions/samuel/`.

## 1. Churn Truth Lab (sem instalar nada)

Abra `solution/truth-lab/index.html` com dois cliques.

Não precisa de servidor, backend nem internet. Os dados já vêm calculados em `solution/truth-lab/data/`. Funciona em Edge e Chrome (testados); Firefox e Safari não foram testados formalmente.

## 2. Requisitos para reprodução em Python

- Python **3.12** (validado com 3.12.10).
- Dependências em `solution/requirements.txt`: numpy, pandas, scipy, scikit-learn, statsmodels e openpyxl, com as versões fixadas em que todos os resultados foram reproduzidos.
- Edge ou Chrome instalado, só para os testes funcionais do Truth Lab (modo headless).

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    |    macOS/Linux: source .venv/bin/activate
pip install -r solution/requirements.txt
```

## 3. Verificações que **não** precisam dos dados

Usam os outputs validados que vêm em `solution/outputs/`.

```bash
python solution/scripts/check_truth_lab.py        # Truth Lab: números, frases proibidas, moeda, offline, arquivos e testes funcionais no navegador
python solution/scripts/final_rewrite_check.py    # afirmações numéricas do README, do diagnóstico e do apêndice contra os outputs, mais as checagens da planilha
python solution/scripts/auditor_integration_check.py  # afirmações dos achados F-18 a F-22 contra os outputs
python solution/scripts/closeout_check.py         # frases desatualizadas ou proibidas no conteúdo atual
python solution/scripts/package_check.py          # pacote autocontido: template, links, arquivos, segredos, escopo do PR (rodar por último)
```

**Resultado esperado:**

| Script | PASS significa |
|---|---|
| `check_truth_lab.py` | Imprime `TOTAL 213 / 213` e termina com código 0. A parte funcional abre a página em headless com a rede desligada; sem navegador, esse grupo falha e o script avisa |
| `final_rewrite_check.py` | `claims: {'VERIFIED': 55}`, as 8 checagens da planilha com PASS e nenhum `MUST FIX` |
| `auditor_integration_check.py` | `claims: {'VERIFIED': 40}` e nenhum `MUST FIX` |
| `closeout_check.py` | Nenhum `MUST FIX` e código de saída 0 |
| `package_check.py` | `TOTAL n / n` e código de saída 0. Falha se houver `__pycache__` deixado pelos outros scripts; apague antes de commitar |

## 4. Reprodução a partir dos dados brutos

Siga `solution/data/README.md`: baixe os 5 CSVs do Kaggle, confira o SHA-256 e coloque-os em `solution/data/ravenstack/`, ou defina `RAVENSTACK_DATA` com a pasta onde estão.

Rode nesta ordem:

| Ordem | Comando | O que gera | Tempo medido |
|---|---|---|---|
| 1 | `python solution/scripts/final_rewrite_build.py` | `outputs/final_rewrite/final_numbers.json` (definições, filas V1/V2/V3, cenários, piloto) **e regenera** `RavenStack_CS_Action_Queues.xlsx` | ~7 s |
| 2 | `python solution/scripts/auditor_integration.py` | `outputs/auditor_integration/` (F-18 a F-22, segmentos, flags por conta) | ~46 s |
| 3 | `python solution/scripts/independent_audit.py` | `outputs/independent_audit/` (mecanismo de datas e null calibrado de Q4 com 1.000 simulações; `--sims N` reduz) | ~11 min |
| 4 | `python solution/scripts/end_to_end_sweep.py` | `outputs/end_to_end_sweep/` (varredura das 5 tabelas, série trimestral, 9 modelos contra o null) | ~11 min |
| 5 | `python solution/scripts/unblocked_models.py` | `outputs/unblocked_models/` (random forest e gradient boosting contra o null, GEE, séries temporais; importa `end_to_end_sweep.py`) | ~19 min |
| 6 | `python solution/scripts/build_truth_lab_data.py` | `truth-lab/data/truth_lab_data.json` e `.js` (verifica cada agregado contra os outputs antes de gravar) | ~1 min |
| 7 | `python solution/scripts/check_truth_lab.py` | Testes do Truth Lab | ~1 min |

Os passos 1 a 5 foram reexecutados a partir desta pasta, numa cópia limpa com os CSVs do Kaggle. Todos os arquivos que eles regeneram saíram **byte a byte** iguais aos enviados: `final_numbers.json`, `auditor_integration_summary.json`, os 14 arquivos de `independent_audit/`, os 17 de `end_to_end_sweep/` e os 6 que `unblocked_models.py` grava. Os tempos foram medidos numa máquina Windows com Python 3.12. O `independent_audit.py` usa um insumo intermediário validado de um pipeline anterior, enviado em `outputs/outcome_reconciliation/event_contract_alignment.csv`.

Todos os scripts usam sementes fixas. A reexecução dos 15 modelos preditivos deu 54/54 valores idênticos.

## 5. Estrutura

```
solution/
├── README.md                 ← este arquivo
├── EXECUTIVE-DIAGNOSIS.md
├── RavenStack_CS_Action_Queues.xlsx
├── requirements.txt
├── truth-lab/                ← index.html, assets/, data/, README.md
├── scripts/                  ← _paths.py (caminhos do pacote) + 11 scripts
├── outputs/                  ← outputs validados usados pelos verificadores e pelo build do Truth Lab
└── data/                     ← README.md + SHA256SUMS.txt (CSVs não incluídos)
```
