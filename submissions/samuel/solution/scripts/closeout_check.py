"""FINAL-CLOSEOUT-TRUTH-LAB-01 — global stale-phrase scan over CURRENT content (item 27).

Scope (package version): every markdown file in submissions/samuel/ plus the Truth Lab UI files
(html, js, json).

Each occurrence is classified CURRENT CORRECT / HISTORICAL / MUST FIX by declared rules. Exit 1 if any MUST FIX.
Run: python solution/scripts/closeout_check.py
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

from _paths import OUTPUTS, PKG, RAW_DIR, ROOT  # noqa: E402,F401  (package paths)
OUT = OUTPUTS / "closeout"
LAB = PKG / "solution" / "truth-lab"

PATTERNS = {
    "four definitions": r"four (churn )?definitions|4 churn definitions|quatro definições",
    "still paying": r"still paying|continua[m]? pagando",
    "old AUC range": r"0[.,]45 ?[–-] ?0[.,]54|0[.,]45 a 0[.,]54",
    "Revenue at Risk": r"revenue at risk|receita em risco",
    "high churn risk": r"high churn risk|alto risco",
    "churn probability": r"churn probability|probabilidade de churn",
    "likely to churn": r"likely to churn",
    "real churn = 0": r"real churn = 0|zero customers churned",
    "Truth Lab not built": r"truth lab not built|ainda não (foi )?constru|still not built|to be built|next deliverable|próximo entregável|next stage: build",
    "prediction is unsafe": r"unsafe",
    "what is at stake": r"at stake",
    "409/899 as economic V3": r"\b409\b|\b899\b",
    "currency": r"R\$|\bBRL\b|\bUSD\b",
    # FINAL-README-SYNC-01
    "CEO metric overstated": r"não mede perda de cliente|não medem nada|measure nothing|does not measure customer loss",
    "zero-active wording": r"não permitem enxergar|não permitem enxergá-la",
    "reason p 2dp": r"p ?= ?0,95(?![0-9])",
    "Enterprise 'only value' wording": r"o que importa é o valor da conta|what matters is account value",
    "Truth Lab tool attribution": r"^(?!.*Antigravity)(?=.*Truth Lab).*Claude Code",
}
NEGATED = re.compile(r"\bn[ãa]o\b|\bnot\b|\bno\b|\bnunca\b|\bnever\b|forbidden|proibid|não construir|do not|bloque|blocked|sem |without|nenhum", re.I)
CORRECTION = re.compile(r"→|substitu|errou|\bantig[oa]s?\b|impreciso|não verificável|Problema|superseded|errata|corrigid|trocad|replaced|foi corrigido|ex-|deixou de", re.I)
PATTERN_LIST = re.compile(r"Lista:|lista de frases|item 27|Varredura|scan|padr(ão|ões)", re.I)


def current_files() -> list[Path]:
    # package scope: every markdown file in submissions/samuel/ (outputs excluded) + the Truth Lab UI files
    fs = sorted(p for p in PKG.rglob("*.md") if "outputs" not in p.relative_to(PKG).parts)
    fs += [LAB / "index.html", LAB / "assets" / "js" / "app.js", LAB / "data" / "truth_lab_data.json"]
    return [f for f in fs if f.exists()]


def classify(rel: str, kind: str, line: str, in_superseded: bool, parent: str = "") -> tuple[str, str]:
    if in_superseded:
        return "HISTORICAL", "inside a SUPERSEDED <details> block"
    if rel.endswith("app.js") and (re.search(r"const FORBIDDEN|forbiddenHits|ok\(", line) or re.fullmatch(r"\s*('[^']*',\s*)+('[^']*'\];?)?\s*", line)):
        return "CURRENT CORRECT", "self-test code / list of phrases the self-test searches for"
    if rel.endswith(".json") and kind == "409/899 as economic V3" and re.search(r'"(value_rank|exposure_rank|usage_rows|usage_count|errors|features|tickets)":(409|899)\b', line):
        return "CURRENT CORRECT", "unrelated numeric field (e.g. an account's value rank), not the V3 population"
    if parent and re.search(r"n[ãa]o construir|do not build", parent, re.I):
        return "CURRENT CORRECT", "list item under a 'do not build' parent"
    if rel in {"docs/TRUTH-LAB-VALIDATION.md", "docs/FINAL-SUBMISSION-CHECKLIST.md"} and (PATTERN_LIST.search(line) or line.count(",") >= 4):
        return "CURRENT CORRECT", "validation doc listing the scanned patterns"
    if kind == "409/899 as economic V3":
        if re.search(r"\b388\b|incluindo trials|including zero-MRR|inclui|qualquer registro|any active|409 → 21|409/388|409/899|409 / 899|21 das 409|Das 409", line, re.I):
            return "CURRENT CORRECT", "409/899 shown only as 'any auto_renew=false incl. zero-MRR trials', next to 388/764"
        return "MUST FIX", "409/899 used without the economic-V3 distinction"
    if kind == "currency":
        if re.search(r"moeda|currency|refund_amount_usd|Forbidden|proibid|R\$ / BRL / USD|sem moeda", line, re.I):
            return "CURRENT CORRECT", "currency named only to forbid it / describe its absence"
        return "MUST FIX", "currency attached to a value"
    if kind == "old AUC range":
        return ("CURRENT CORRECT", "correction narrative") if CORRECTION.search(line) else ("MUST FIX", "stale AUC range")
    if kind in {"four definitions", "Truth Lab not built", "prediction is unsafe", "what is at stake", "still paying"}:
        # correction narrative: the line also carries the replacement wording, or describes the review that removed it
        replacement = re.search(r"Três sinais de churn|três sinais|três populações de churn conflitantes|não é suportada|pode representar|ainda possuem registros|Histórico financeiro|"
                                r"Nenhuma ocorrência atual|mais dramáticos que a evidência|menos dramática|Apontou que", line, re.I)
        if CORRECTION.search(line) or replacement or re.search(r"Auditor independente \||\| Problema|Como apareceu", line):
            return "CURRENT CORRECT", "correction narrative / error table"
        return "MUST FIX", "superseded wording in current content"
    if kind in {"CEO metric overstated", "zero-active wording", "reason p 2dp", "Enterprise 'only value' wording", "Truth Lab tool attribution"}:
        replacement = re.search(r"interpretados de forma confiável|identificar de forma confiável perda completa|concentração de valor é mais útil|"
                                r"p = 0,955|Antigravity", line)
        if CORRECTION.search(line) or replacement or re.search(r"Antes \||\| Antes|substituíd", line, re.I):
            return "CURRENT CORRECT", "correction narrative (line also carries the replacement wording)"
        return "MUST FIX", "superseded executive wording (FINAL-README-SYNC-01)"
    if kind in {"Revenue at Risk", "high churn risk", "churn probability", "likely to churn", "real churn = 0"}:
        if NEGATED.search(line) or re.search(r"Forbidden wording|NOT SUPPORTED", line):
            return "CURRENT CORRECT", "negated / listed as forbidden or not to build"
        return "MUST FIX", "affirmative risk / probability claim"
    return "MUST FIX", "unclassified"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for f in current_files():
        rel = f.relative_to(ROOT).as_posix()
        text = f.read_text(encoding="utf-8-sig")
        if f.suffix == ".json":
            # one metric / account object per unit, so a field is read together with its own limitation text
            lines = re.split(r'(?<=\}),(?=")', text)
        else:
            lines = text.splitlines()
        sup = False
        for n, line in enumerate(lines, 1):
            parent = ""
            if f.suffix == ".md" and line.lstrip().startswith("- "):
                for k in range(n - 2, max(n - 14, -1), -1):
                    if not lines[k].lstrip().startswith("- "):
                        parent = lines[k]
                        break
            if "<details>" in line:
                sup = True
            for kind, rx in PATTERNS.items():
                if re.search(rx, line, re.I):
                    st, why = classify(rel, kind, line, sup, parent)
                    rows.append({"file": rel, "line": n, "pattern": kind, "status": st, "reason": why, "text": line.strip()[:200]})
            if "</details>" in line:
                sup = False
    with (OUT / "closeout_stale_scan.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["file", "line", "pattern", "status", "reason", "text"]); w.writeheader(); w.writerows(rows)
    counts = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print("files scanned:", len(current_files()), "| occurrences:", counts)
    bad = [r for r in rows if r["status"] == "MUST FIX"]
    for r in bad:
        print("MUST FIX", r["file"], r["line"], r["pattern"], "|", r["text"][:140])
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
