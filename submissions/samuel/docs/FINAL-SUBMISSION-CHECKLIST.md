# Checklist final de submissão — Samuel Santos — Challenge 001

Data: 04/10/2026. Os itens marcados foram confirmados por verificação; a evidência está ao lado de cada um.

## Checklist oficial (submission-guide.md)

- [x] Escolhi um challenge e li o README completo — Challenge 001, Diagnóstico de Churn. O enunciado é a fonte de todo o trabalho.
- [x] Minha solução está na pasta `submissions/samuel/` — pacote autocontido.
- [x] Incluí o Process Log com evidência válida — narrativa escrita em `process-log/PROCESS-LOG.md` e `process-log/TRUTH-LAB-BUILD.md`.
- [x] O README segue o template — seções, ordem, LinkedIn, challenge e data conferidos por `package_check.py`.
- [x] Código tem instruções de setup — `solution/README.md` e `solution/requirements.txt`.
- [x] Nenhuma mudança necessária fora da pasta — testado num repositório git temporário do template oficial: 105 arquivos staged, 0 fora de `submissions/samuel/`, 0 `.env`.

## Verificações adicionais

- [x] O Truth Lab abre localmente — `solution/truth-lab/index.html` por `file://`.
- [x] O Truth Lab funciona offline — testes funcionais rodam com a rede desligada no navegador; nenhuma URL externa.
- [x] Os testes automáticos passam — `check_truth_lab.py` 213/213; `final_rewrite_check.py` 55/55; `auditor_integration_check.py` 40/40; `closeout_check.py` 0 MUST FIX.
- [x] Os links do README e dos demais documentos resolvem — `package_check.py`.
- [x] Sem segredos — nenhuma chave, token, chave privada, `.env`, caminho local ou e-mail corporativo no pacote; metadados da planilha limpos.
- [x] LinkedIn preenchido — https://www.linkedin.com/in/samuelscs-ops/
- [x] Process Log narrativo presente — 10 seções cronológicas e pelo menos 19 ciclos documentados.
- [x] Scripts presentes — `solution/scripts/`, com 11 scripts (incluindo `package_check.py`) e `_paths.py`.
- [x] Requirements presente — só as bibliotecas importadas, com versões fixadas.
- [x] Dados brutos não enviados — instruções e SHA-256 em `solution/data/`.

## Passos para abrir o PR (a executar por Samuel; não foram executados)

1. Fork de `ai-master-challenge` e clone do fork.
2. `git checkout -b submission/samuel`
3. Copiar esta pasta para `submissions/samuel/` no clone.
4. Apagar caches de Python, se algum script foi rodado: `find submissions/samuel -name __pycache__ -exec rm -rf {} +`
5. Rodar `python submissions/samuel/solution/scripts/package_check.py` → deve terminar em `TOTAL n / n`.
6. **`git add -f submissions/samuel`**. O `.gitignore` do repositório oficial contém `submissions/`, então um `git add` comum não adiciona nada. **Não** edite o `.gitignore`: isso altera um arquivo fora da sua pasta e o PR seria rejeitado.
7. `git status` → só caminhos `submissions/samuel/...`.
8. `git commit -m "[Submission] Samuel Santos — Challenge 001"` e `git push origin submission/samuel`.
9. Abrir o Pull Request para `main` com o título `[Submission] Samuel Santos — Challenge 001`.
