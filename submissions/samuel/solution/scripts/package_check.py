"""FINAL-SUBMISSION-PACKAGE-01 — self-containment checks for submissions/samuel/.

1. Template compliance of README.md (official submission template sections, LinkedIn, challenge, date).
2. Every relative link in every markdown file resolves inside the package; no absolute or workspace paths.
3. Required files exist.
4. Secret / personal-data scan (keys, tokens, private keys, .env files, local user paths).
5. Truth Lab: index.html references only local files that exist; no external URL.
6. PR scope: nothing the README points to lives outside submissions/samuel/.

Exit 1 on any failure.  Run from submissions/samuel/:  python solution/scripts/package_check.py
"""
from __future__ import annotations

import re
import sys

sys.dont_write_bytecode = True  # this check must not leave __pycache__ behind
from pathlib import Path  # noqa: E402

PKG = Path(__file__).resolve().parents[2]  # submissions/samuel (no _paths import, so no .pyc is written)

results: list[tuple[str, str, bool, str]] = []


def check(group: str, name: str, cond: bool, detail: str = "") -> None:
    results.append((group, name, bool(cond), detail))


def template() -> None:
    t = (PKG / "README.md").read_text(encoding="utf-8")
    for h in ["# Submissão — Samuel Santos — Challenge 001", "## Sobre mim", "## Executive Summary", "## Solução", "### Abordagem",
              "### Resultados / Findings", "### Recomendações", "### Limitações", "## Process Log — Como usei IA", "### Ferramentas usadas",
              "### Workflow", "### Onde a IA errou e como corrigi", "### O que eu adicionei que a IA sozinha não faria", "## Evidências"]:
        check("template", f"README has '{h}'", re.search(rf"(?m)^{re.escape(h)}\s*$", t) is not None)
    order = [t.find(h) for h in ["## Sobre mim", "## Executive Summary", "## Solução", "## Process Log — Como usei IA", "## Evidências"]]
    check("template", "sections in template order", order == sorted(order) and -1 not in order, order)
    check("template", "LinkedIn filled", "**LinkedIn:** https://www.linkedin.com/in/samuelscs-ops/" in t)
    check("template", "challenge filled", "**Challenge escolhido:** 001 — Diagnóstico de Churn" in t)
    check("template", "name filled", "**Nome:** Samuel Santos" in t)
    check("template", "submission date", t.rstrip().endswith("_Submissão enviada em: 04/10/2026_"))
    check("template", "no placeholder left", not re.search(r"_adicionar antes do envio_|\[Seu Nome\]|\[XXX\]|LinkedIn pending|\[data\]", t))
    es = t.split("## Executive Summary", 1)[1].split("###", 1)[0]
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", es.strip()) if len(s) > 20]
    check("template", "Executive Summary has 3–5 sentences", 3 <= len(sentences) <= 5, len(sentences))


def links() -> None:
    mds = [p for p in PKG.rglob("*.md") if "outputs" not in p.relative_to(PKG).parts]
    n = 0
    for f in mds:
        text = f.read_text(encoding="utf-8")
        for m in re.finditer(r"\]\(([^)\s]+)\)", text):
            tgt = m.group(1).split("#")[0]
            if not tgt or tgt.startswith(("http://", "https://", "mailto:")):
                continue
            n += 1
            dest = (f.parent / tgt).resolve()
            inside = PKG.resolve() in dest.parents or dest == PKG.resolve()
            check("links", f"{f.relative_to(PKG).as_posix()} → {tgt}", dest.exists() and inside, "missing" if not dest.exists() else "outside package")
        bad = re.findall(r"[A-Za-z]:\\\\Users|[A-Za-z]:/Users|/home/\w+|/Users/\w+|(?<!-b )(?<!origin )submission/samuel|\.\./\.\./", text)  # branch name "submission/samuel" (official guide) is allowed
        check("paths", f"no absolute/workspace path in {f.relative_to(PKG).as_posix()}", not bad, bad[:3])
    check("links", f"{n} relative links checked", n > 10, n)


def required() -> None:
    for rel in ["README.md", "solution/README.md", "solution/EXECUTIVE-DIAGNOSIS.md", "solution/RavenStack_CS_Action_Queues.xlsx", "solution/requirements.txt",
                "solution/truth-lab/index.html", "solution/truth-lab/README.md", "solution/truth-lab/assets/css/app.css", "solution/truth-lab/assets/js/app.js",
                "solution/truth-lab/data/truth_lab_data.json", "solution/truth-lab/data/truth_lab_data.js", "solution/data/README.md", "solution/data/SHA256SUMS.txt",
                "solution/scripts/_paths.py", "solution/scripts/final_rewrite_build.py", "solution/scripts/auditor_integration.py",
                "solution/scripts/independent_audit.py", "solution/scripts/end_to_end_sweep.py", "solution/scripts/unblocked_models.py",
                "solution/scripts/build_truth_lab_data.py", "solution/scripts/check_truth_lab.py", "solution/scripts/closeout_check.py",
                "solution/scripts/final_rewrite_check.py", "solution/scripts/auditor_integration_check.py",
                "solution/outputs/final_rewrite/final_numbers.json", "solution/outputs/auditor_integration/auditor_integration_summary.json",
                "solution/outputs/end_to_end_sweep/quarterly_claims.csv", "solution/outputs/outcome_reconciliation/event_contract_alignment.csv",
                "process-log/PROCESS-LOG.md", "process-log/TRUTH-LAB-BUILD.md",
                "docs/TECHNICAL-APPENDIX.md", "docs/FINAL-EVIDENCE-REGISTER.md", "docs/TRUTH-LAB-REQUIREMENTS.md", "docs/TRUTH-LAB-VALIDATION.md",
                "docs/FINAL-SUBMISSION-CHECKLIST.md"]:
        check("files", f"{rel} exists", (PKG / rel).is_file())
    reqs = (PKG / "solution" / "requirements.txt").read_text(encoding="utf-8")
    imported = set()
    for py in (PKG / "solution" / "scripts").glob("*.py"):
        imported |= set(re.findall(r"(?m)^(?:from|import) (numpy|pandas|scipy|sklearn|statsmodels|openpyxl|matplotlib|seaborn)\b", py.read_text(encoding="utf-8")))
    names = {"sklearn": "scikit-learn"}
    check("files", "every third-party import is pinned in requirements.txt", all(f"{names.get(m, m)}==" in reqs for m in imported), sorted(imported))
    check("files", "requirements.txt has no unused library", all(re.sub(r"==.*", "", l).strip() in {names.get(m, m) for m in imported}
                                                                  for l in reqs.splitlines() if l.strip() and not l.startswith("#")))
    check("files", "raw CSVs not shipped", not list(PKG.rglob("ravenstack_*.csv")))
    cache = [x.relative_to(PKG).as_posix() for x in PKG.rglob("*") if x.name == "__pycache__" or x.suffix == ".pyc"]
    check("files", "no __pycache__ / .pyc (git add -f would commit them; delete before committing)", not cache, cache[:3])


SECRET = re.compile(r"sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|github_pat_|AKIA[0-9A-Z]{16}|xox[baprs]-|-----BEGIN [A-Z ]*PRIVATE KEY-----|"
                    r"(?i:(api[_-]?key|secret|password|passwd|token)\s*[:=]\s*['\"][^'\"]{8,})")


def secrets() -> None:
    envs = [p for p in PKG.rglob(".env*")]
    check("secrets", "no .env file inside the package", not envs, envs)
    hits = []
    for f in PKG.rglob("*"):
        if f.is_file() and f.name != "package_check.py" and f.suffix.lower() in {".md", ".py", ".txt", ".json", ".js", ".css", ".html", ".csv"}:  # this file holds the patterns
            t = f.read_text(encoding="utf-8", errors="ignore")
            if SECRET.search(t) or re.search(r"AppData|C:\\\\Users|@v4company", t):
                hits.append(f.relative_to(PKG).as_posix())
    check("secrets", "no keys, tokens, private keys, user paths or corporate e-mail", not hits, hits[:5])


def truth_lab() -> None:
    lab = PKG / "solution" / "truth-lab"
    idx = (lab / "index.html").read_text(encoding="utf-8")
    refs = re.findall(r'(?:src|href)="([^"#]+)"', idx)
    check("truth-lab", "index.html references only local files that exist", refs and all((lab / r).is_file() for r in refs), refs)
    ext = [r for p in lab.rglob("*") if p.is_file() and p.suffix in {".html", ".js", ".css", ".json"}
           for r in re.findall(r"https?://[^\s\"')]+", p.read_text(encoding="utf-8")) if "www.w3.org/2000/svg" not in r]
    check("truth-lab", "no external URL in Truth Lab files", not ext, ext[:3])


def pr_scope() -> None:
    t = (PKG / "README.md").read_text(encoding="utf-8")
    outside = [m for m in re.findall(r"\]\(([^)\s]+)\)", t) if not m.startswith("http") and ((PKG / m.split("#")[0]).resolve() != PKG.resolve()
               and PKG.resolve() not in (PKG / m.split("#")[0]).resolve().parents)]
    check("pr-scope", "README needs nothing outside submissions/samuel/", not outside, outside)


def main() -> None:
    template(); links(); required(); secrets(); truth_lab(); pr_scope()
    groups: dict[str, list[int]] = {}
    for g, _, ok, _ in results:
        groups.setdefault(g, [0, 0])[0 if ok else 1] += 1
    for g, (p, f) in groups.items():
        print(f"{g:10s} PASS {p:3d}  FAIL {f}")
    fails = [r for r in results if not r[2]]
    for g, n, _, d in fails:
        print("FAIL", g, n, d)
    print("TOTAL", len(results) - len(fails), "/", len(results))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
