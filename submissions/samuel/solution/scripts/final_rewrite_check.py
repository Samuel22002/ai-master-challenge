"""FINAL-REWRITE-01 — claim register, global stale-phrase validation and challenge scorecard.

1. Every number quoted in the rewritten submission is re-derived from final_numbers.json,
   formatted the way the text writes it, and searched in the files where it must appear.
2. Global scan for the phrases/numbers listed in FINAL-REWRITE-01 (markdown + new workbook),
   each occurrence classified CORRECT CURRENT / HISTORICAL / MUST FIX by declared rules.
3. Challenge scorecard (analyst judgement), current vs expected after the Truth Lab.

Run: python solution/scripts/final_rewrite_check.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

from _paths import OUTPUTS, PKG, RAW_DIR, ROOT  # noqa: E402,F401  (package paths)
OUT = OUTPUTS / "final_rewrite"
SUB = PKG
FILES = {"README": SUB / "README.md", "EXEC": SUB / "solution" / "EXECUTIVE-DIAGNOSIS.md", "APPX": SUB / "docs" / "TECHNICAL-APPENDIX.md",
         "LAB": SUB / "docs" / "TRUTH-LAB-REQUIREMENTS.md", "LOG": SUB / "process-log" / "PROCESS-LOG.md"}
XLSX = SUB / "solution" / "RavenStack_CS_Action_Queues.xlsx"
ERRATA_MARKS = ("<!-- ERRATA-2026-10-04 -->", "<!-- ERRATA-FINAL-REWRITE-2026-10-04 -->")


def br_int(x: float) -> str:
    return f"{round(x):,}".replace(",", ".")


def br_pct(x: float, d: int = 1) -> str:
    return f"{100 * x:.{d}f}%".replace(".", ",")


def claims(N: dict) -> list[tuple]:
    sc = N["scenarios_on_V3"]
    c = N["churn_definitions"]
    return [
        ("C01", "churn_flag accounts", str(c["churn_flag"]), ["README", "EXEC"]),
        ("C02", "accounts with churn event", str(c["any_churn_event"]), ["README", "EXEC"]),
        ("C03", "accounts with subscription end", str(c["any_subscription_end"]), ["README", "EXEC"]),
        ("C04", "accounts with zero active records", f"| **{c['zero_active_records_2024_12_31']}** |", ["EXEC"]),
        ("C05", "overlap flag∩event", f"flag ∩ evento = {c['flag_and_event']}", ["README", "EXEC"]),
        ("C06", "overlap flag∩end", f"flag ∩ encerramento = {c['flag_and_end']}", ["README", "EXEC"]),
        ("C07", "overlap event∩end", f"evento ∩ encerramento = {c['event_and_end']}", ["README", "EXEC"]),
        ("C08", "all three", f"nas três = {c['all_three']}", ["README", "EXEC"]),
        ("C09", "V1 MRR proxy", br_int(N["V1"]["active_mrr_proxy"]), ["README", "EXEC"]),
        ("C10", "V1 share", br_pct(N["V1"]["share_active"]), ["README", "EXEC"]),
        ("C11", "V1 flagged with zero active MRR = 0 (100% paying)", "110 (100% das flagged)", ["README"]),
        ("C12", "V2 MRR proxy", br_int(N["V2"]["active_mrr_proxy"]), ["README", "EXEC"]),
        ("C13", "V2 share", br_pct(N["V2"]["share_active"]), ["README", "EXEC"]),
        ("C14", "V3 accounts", f"{N['V3']['accounts']} contas · {N['V3']['records_with_mrr']} registros", ["README"]),
        ("C15", "V3 exposed MRR proxy", br_int(N["V3"]["exposed_mrr_proxy"]), ["README", "EXEC", "LAB"]),
        ("C16", "V3 share", br_pct(N["V3"]["share_active"]), ["README", "EXEC"]),
        ("C17", "any non-auto accounts (incl. zero MRR)", str(N["V3"]["any_nonauto_accounts"]), ["README", "EXEC"]),
        ("C18", "trial-only accounts", f"{N['V3']['trial_only_accounts']} possuem somente exposições", ["README", "EXEC"]),
        ("C19", "V3-W1 exposed", br_int(N["V3W1"]["exposed_mrr_proxy"]), ["README", "EXEC"]),
        ("C20", "V3-W1 share of V3", br_pct(N["V3W1"]["share_of_V3"]), ["README", "EXEC"]),
        ("C21", "V3-W1 records", f"50 contas · {N['V3W1']['records']} registros", ["README"]),
        ("C22", "wave 1 union", f"{N['wave1']['union_accounts']} contas únicas", ["EXEC"]),
        ("C23", "wave 1 not naive sum", f"Não são {N['wave1']['naive_sum']}", ["EXEC"]),
        ("C24", "overlaps V1∩V2 / V1∩W1 / V2∩W1 / triple",
         f"V1∩V2 = {N['wave1']['V1_V2']}, V1∩V3-W1 = {N['wave1']['V1_W1']}, V2∩V3-W1 = {N['wave1']['V2_W1']}, nas três = {N['wave1']['triple']}", ["README", "EXEC"]),
        ("C25", "scenario 5%", br_int(sc[0]["mrr_proxy"]), ["README", "EXEC"]),
        ("C26", "scenario 10%", br_int(sc[1]["mrr_proxy"]), ["README", "EXEC"]),
        ("C27", "scenario 15%", br_int(sc[2]["mrr_proxy"]), ["README", "EXEC"]),
        ("C28", "scenario annualized 5/10/15", f"{br_int(sc[0]['annualized_proxy'])}, {br_int(sc[1]['annualized_proxy'])} ou {br_int(sc[2]['annualized_proxy'])}", ["EXEC"]),
        ("C29", "pilot population", f"{N['pilot']['population']} contas", ["README", "EXEC", "APPX"]),
        ("C30", "pilot per arm", f"{N['pilot']['per_arm']} por braço", ["README", "EXEC"]),
        ("C31", "pilot exposed", br_int(N["pilot"]["exposed_mrr_proxy"]), ["APPX"]),
        ("C32", "MDE 10/15/20", f"~{str(N['pilot']['mde_pp']['0.1']).replace('.', ',')}, {str(N['pilot']['mde_pp']['0.15']).replace('.', ',')} ou {str(N['pilot']['mde_pp']['0.2']).replace('.', ',')}", ["EXEC"]),
        ("C33", "Enterprise any active record", f"{N['enterprise']['accounts_any_active_record']}/500", ["README"]),
        ("C34", "Enterprise active record MRR>0", f"{N['enterprise']['accounts_active_record_mrr_gt0']} com MRR proxy > 0", ["README"]),
        ("C35", "Enterprise share", br_pct(N["enterprise"]["share_active_mrr"]), ["README"]),
        ("C36", "P(end) by plan p", f"p = {N['enterprise']['chi2_p']:.3f}".replace(".", ","), ["README"]),
        ("C37", "ended 2024 reference", br_int(N["ended_2024"]["mrr_proxy"]), ["EXEC"]),
        ("C38", "ended 2024 right-after share", br_pct(N["ended_2024"]["share_with_other_active_record_right_after"]), ["EXEC"]),
        ("C39", "usage segments declining", f"{N['usage']['segments_declining']} de {N['usage']['segments_tested']} segmentos", ["EXEC"]),
        ("C40", "usage segment range", f"−{abs(int(N['usage']['segment_change_max_pct']))}% a −{abs(int(N['usage']['segment_change_min_pct']))}%", ["README", "EXEC"]),
        ("C41", "usage quarterly total range", f"{br_int(N['usage']['quarterly_total_min'])}–{br_int(N['usage']['quarterly_total_max'])}", ["README", "EXEC"]),
        ("C42", "usage coverage (pt-BR format)", br_pct(N["usage"]["usage_rows_inside_subscription_life"], 2), ["README", "APPX"]),
        ("C42b", "usage coverage label (English format, Truth Lab spec)", f"{100 * N['usage']['usage_rows_inside_subscription_life']:.2f}%", ["LAB"]),
        ("C43", "CSAT missing", br_pct(N["support"]["csat_missing_share"], 2), ["README", "EXEC"]),
        ("C44", "health score readiness", f"{N['health_score_readiness']['green']} GREEN · {N['health_score_readiness']['partial']} PARTIAL · {N['health_score_readiness']['red']} RED", ["README", "APPX", "LAB"]),
        ("C45", "top10 / top20 / top50 concentration",
         f"top 10 contas = {br_pct(N['concentration']['top10']['share'])}", ["README"]),
    ] + [
        (f"C46-{i}", f"observed rate {r['segment']}", br_pct(r["rate"]), ["README", "APPX"])
        for i, r in enumerate(N["observed_segment_rates"]["top5_n_ge_30"], 1)
    ] + [
        ("C47", "overall churn_flag rate", br_pct(N["observed_segment_rates"]["overall_churn_flag_rate"]), ["README", "EXEC", "APPX"]),
        ("C48", "minimum dimension q", f"q = {N['observed_segment_rates']['min_dimension_q']:.2f}".replace(".", ","), ["README", "EXEC"]),
        ("C49", "dimensions with p<0.05", f"Dimensões com p < 0,05 | **{N['observed_segment_rates']['dimensions_with_p_lt_05']}**", ["APPX"]),
        ("C50", "DevTools CI", f"{br_pct(N['observed_segment_rates']['top5_n_ge_30'][0]['ci95'][0])}–{br_pct(N['observed_segment_rates']['top5_n_ge_30'][0]['ci95'][1])}", ["README"]),
    ]


PATTERNS = {"409": r"\b409\b", "899": r"\b899\b", "456": r"\b456\b", "389": r"\b389\b", "R$": r"R\$", "BRL": r"\bBRL\b", "USD": r"\bUSD\b|US\$|\busd\b",
            "Revenue at Risk": r"Revenue at Risk|receita em risco", "high churn risk": r"alto risco|high[- ]churn[- ]risk|high[- ]risk",
            "churn probability": r"churn probability|probabilidade de churn", "Enterprise priority": r"Enterprise",
            "1.13M as lost revenue": r"1[,.]13 ?mi|1[,.]13M|1\.127\.644|1,127,644", "0/10 health score": r"0/10|0 de 10",
            "388": r"\b388\b", "764": r"\b764\b", "394": r"\b394\b", "176": r"\b176\b"}
NEG = re.compile(r"\bn[ãa]o\b|\bnot\b|\bno\b|nenhum|NOT SUPPORTED|DO NOT|bloque|sem |não construir|nunca|~~", re.I)
EXPLAIN_COUNT = re.compile(r"trial|algum registro ativo sem auto-renew|any active|qualquer|incl|21 ", re.I)
HIST_DOC = re.compile(r"^docs/(0\d|1[0-7]|11b)[-_]|^docs/(GLOBAL-CONSISTENCY-REPORT|FINAL-CORRECTION-VALIDATION|SECOND-OPINION)|^process-log/(0\d|1\d|SECOND|FINAL-AUDIT)|^research/")
OUT_OF_SCOPE = {"docs/FINAL-EVIDENCE-REGISTER.md", "CLAUDE.md", "AGENTS.md"}


CORRECTION_NARRATIVE = re.compile(r"→|substitu|e não \"|proposta|onde a exposição real|refeita|Fila \"Enterprise\"|onde a IA errou", re.I)
TABLE_DATA = re.compile(r"^\|\s*[A-Za-z]+\s*\|\s*[−-]\d+%")


def classify(rel: str, kind: str, line: str, in_banner: bool, has_errata: bool, context: str = "") -> tuple[str, str]:
    if in_banner:
        return "HISTORICAL", "inside errata banner"
    if not rel.startswith("docs/FINAL-EVIDENCE-REGISTER") and CORRECTION_NARRATIVE.search(line):
        return "CORRECT CURRENT", "correction narrative (describes a superseded value and its replacement)"
    if not rel.startswith("docs/FINAL-EVIDENCE-REGISTER") and TABLE_DATA.search(line.replace("| EdTech | −68% | DE | −40% ", "")) or (kind == "Enterprise priority" and re.search(r"\|\s*Enterprise\s*\|\s*[−-]\d+%", line)):
        return "CORRECT CURRENT", "data value in a results table (plan segment), not a prioritisation claim"
    if kind in {"Revenue at Risk", "high churn risk", "churn probability"} and re.search(r"n[ãa]o construir|do not build", context, re.I):
        return "CORRECT CURRENT", "list item under a 'do not build' parent bullet"
    current = not rel.startswith("docs/FINAL-EVIDENCE-REGISTER") or rel in {"README.md"}
    if rel in OUT_OF_SCOPE and kind == "409" and re.search(r"errata.*409/388|409/388.*(pendente|aprovação)|F-16.*n[ãa]o.*alterad", line, re.I):
        return "CORRECT CURRENT", "describes the pending F-16 errata (409/388), not the stale value"
    if rel in OUT_OF_SCOPE:
        # F-16 errata approved and applied 2026-10-04: these documents are now checked like current documents
        if kind in {"409", "899"} and re.search(r"\b388\b|incluindo trials|qualquer registro|409/388|409/899", line, re.I):
            return "CORRECT CURRENT", "F-16 corrected wording: 409/899 only for 'any auto_renew=false record incl. zero-MRR trials', 388/764 as economic V3"
        if kind in {"R$", "BRL", "USD"} and re.search(r"Forbidden wording|refund_amount_usd|moeda", line, re.I):
            return "CORRECT CURRENT", "currency listed as forbidden / describes the currency correction"
        if kind in {"R$", "409", "899", "456"}:
            return "MUST FIX", "stale F-16 value outside the superseded block"
        return "CORRECT CURRENT", "consistent with register semantics"
    if not current:
        if has_errata or HIST_DOC.search(rel):
            return "HISTORICAL", "historical analysis/working document" + (" with errata banner" if has_errata else "")
        return "MUST FIX", "current non-submission document"
    # current submission rules
    if kind in {"388", "764", "394", "176"}:
        return "CORRECT CURRENT", "validated number"
    if kind == "389" and "ticket_before_signup" in line:
        return "CORRECT CURRENT", "different metric: accounts with >=1 ticket before signup (auditor integration), not the old count"
    if kind in {"409", "899", "456", "389"}:
        return ("CORRECT CURRENT", "explains the 409 vs 388 distinction") if EXPLAIN_COUNT.search(line) else ("MUST FIX", "stale count")
    if kind in {"R$", "BRL", "USD"}:
        if re.search(r"refund_amount_usd|moeda|currency|sem moeda|num valor sem moeda", line, re.I):
            return "CORRECT CURRENT", "describes the currency correction / the only explicit currency column"
        return "MUST FIX", "invented currency on MRR proxy"
    if kind in {"Revenue at Risk", "high churn risk", "churn probability"}:
        return ("CORRECT CURRENT", "negated / listed as not to build") if NEG.search(line) else ("MUST FIX", "affirmative risk claim")
    if kind == "Enterprise priority":
        return ("CORRECT CURRENT", "Enterprise explicitly not used as segment / factual share") if re.search(r"não serve|não difere|74,3%|Enterprise\b.*(—|-)|plano|registro Enterprise|programa", line, re.I) or NEG.search(line) else ("MUST FIX", "Enterprise as priority")
    if kind == "1.13M as lost revenue":
        return ("CORRECT CURRENT", "reference only, explicitly not lost revenue") if re.search(r"referência|não .*receita perdida|reference", line, re.I) else ("MUST FIX", "ended MRR presented as loss")
    if kind == "0/10 health score":
        return "MUST FIX", "old readiness wording"
    return "MUST FIX", "unclassified"


def scan() -> pd.DataFrame:
    rows = []
    roots = [PKG / "docs", PKG / "process-log", PKG / "solution" / "truth-lab", PKG / "solution" / "README.md", PKG / "solution" / "EXECUTIVE-DIAGNOSIS.md", PKG / "README.md"]  # package scope
    files = []
    for r in roots:
        files += [r] if r.is_file() else sorted(r.rglob("*.md"))
    skip = {"docs/TRUTH-LAB-VALIDATION.md", "docs/FINAL-SUBMISSION-CHECKLIST.md"}  # validation docs quote the patterns they check
    for f in files:
        rel = f.relative_to(ROOT).as_posix()
        if rel in skip:
            continue
        lines = f.read_text(encoding="utf-8-sig").splitlines()
        has_errata = any(m in l for l in lines[:6] for m in ERRATA_MARKS)
        banner_end = 0
        if has_errata:
            for i, l in enumerate(lines):
                if any(m in l for m in ERRATA_MARKS):
                    j = i + 1
                    while j < len(lines) and (lines[j].startswith(">") or lines[j].startswith("#") or lines[j].strip() in {"", "---"} or lines[j].startswith("|")) and j < i + 40:
                        if lines[j].strip() == "---":
                            j += 1; break
                        if lines[j].strip() == "" and j + 1 < len(lines) and not (lines[j + 1].startswith(">") or lines[j + 1].startswith("|")):
                            break
                        j += 1
                    banner_end = max(banner_end, j)
        superseded = set()
        inside = False
        for i, l in enumerate(lines, 1):
            if l.strip().startswith("<details>"):
                inside = True
            if inside:
                superseded.add(i)
            if l.strip().startswith("</details>"):
                inside = False
        for n, line in enumerate(lines, 1):
            if n in superseded:
                for kind, rx in PATTERNS.items():
                    if re.search(rx, line):
                        rows.append({"file": rel, "line": n, "pattern": kind, "status": "HISTORICAL", "reason": "inside a SUPERSEDED <details> block (prior wording kept as history)", "text": line.strip()[:180]})
                continue
            # context = nearest preceding non-list line (parent bullet / paragraph) for nested list items
            context = ""
            if line.lstrip().startswith("- "):
                for k in range(n - 2, max(n - 15, -1), -1):
                    prev = lines[k]
                    if not prev.lstrip().startswith("- ") or len(prev) - len(prev.lstrip()) < len(line) - len(line.lstrip()):
                        context = prev; break
            for kind, rx in PATTERNS.items():
                if re.search(rx, line):
                    status, why = classify(rel, kind, line, n <= banner_end and has_errata, has_errata, context)
                    rows.append({"file": rel, "line": n, "pattern": kind, "status": status, "reason": why, "text": line.strip()[:180]})
    wb = load_workbook(XLSX)
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                fmt = cell.number_format or ""
                if re.search(r"R\$|\$|BRL|USD", fmt):
                    rows.append({"file": f"{XLSX.relative_to(ROOT).as_posix()}::{ws.title}", "line": cell.coordinate, "pattern": "currency number format",
                                 "status": "MUST FIX", "reason": "currency in number format", "text": fmt})
                if isinstance(cell.value, str):
                    for kind, rx in PATTERNS.items():
                        if kind in {"388", "764", "394", "176", "Enterprise priority"}:
                            continue
                        if re.search(rx, cell.value):
                            st, why = classify("submission/xlsx", kind, cell.value, False, False)
                            rows.append({"file": f"{XLSX.relative_to(ROOT).as_posix()}::{ws.title}", "line": cell.coordinate, "pattern": kind,
                                         "status": st, "reason": why, "text": cell.value[:180]})
    return pd.DataFrame(rows)


def workbook_checks(N: dict) -> list[dict]:
    wb = load_workbook(XLSX)
    out = []
    expect = {"V1 Status Reconciliation": N["V1"]["accounts"], "V2 Top-Value Coverage": N["V2"]["accounts"], "V3 Renewal Readiness": N["V3"]["accounts"]}
    for name, n in expect.items():
        ws = wb[name]
        rows = sum(1 for r in ws.iter_rows(min_row=5) if r[1].value)
        out.append({"check": f"workbook {name} rows", "expected": n, "observed": rows, "status": "PASS" if rows == n else "FAIL"})
    ws = wb["V3 Renewal Readiness"]
    w1 = sum(1 for r in ws.iter_rows(min_row=5) if r[10].value == "W1")
    pilot = sum(1 for r in ws.iter_rows(min_row=5) if r[13].value == "yes")
    zero = sum(1 for r in ws.iter_rows(min_row=5) if (r[6].value or 0) <= 0 and r[1].value)
    out += [{"check": "workbook V3 wave W1 rows", "expected": N["V3W1"]["accounts"], "observed": w1, "status": "PASS" if w1 == N["V3W1"]["accounts"] else "FAIL"},
            {"check": "workbook V3 pilot-eligible rows", "expected": N["pilot"]["population"], "observed": pilot, "status": "PASS" if pilot == N["pilot"]["population"] else "FAIL"},
            {"check": "workbook V3 rows with exposure <= 0", "expected": 0, "observed": zero, "status": "PASS" if zero == 0 else "FAIL"}]
    sheets = wb.sheetnames
    out.append({"check": "workbook sheets", "expected": "Overview, V1, V2, V3, Definitions & Caveats", "observed": ", ".join(sheets),
                "status": "PASS" if sheets == ["Overview", "V1 Status Reconciliation", "V2 Top-Value Coverage", "V3 Renewal Readiness", "Definitions & Caveats"] else "FAIL"})
    trial = wb["Definitions & Caveats"]
    n_trial = sum(1 for r in trial.iter_rows() if isinstance(r[0].value, str) and r[0].value.startswith("A-") and r[1].value and str(r[1].value).startswith("Company"))
    out.append({"check": "trial-only accounts listed separately", "expected": N["V3"]["trial_only_accounts"], "observed": n_trial,
                "status": "PASS" if n_trial == N["V3"]["trial_only_accounts"] else "FAIL"})
    return out


SCORECARD = [
    ("Root cause", 8, 8, "Management root cause stated as headline (KPI mixes grains, no lifecycle); individual cancellation cause explicitly not identifiable"),
    ("Segments", 7, 7, "Two columns: predicted risk (none validated) vs business priority (value, exposure, status)"),
    ("Specific accounts", 8, 9, "Named V1/V2/V3 lists with declared rules; Truth Lab adds per-account drill-down"),
    ("Concrete actions", 9, 9, "Monday actions with owners and 14-day reconciliation; 30/60/90 roadmap"),
    ("Estimated impact", 7, 7, "Three levels: fact, conditional scenarios, real effect only via pilot"),
    ("5-table crossing", 8, 9, "All five tables used; account brief in Truth Lab will show them in one view"),
    ("CEO usability", 8, 9, "2-page diagnosis without statistical jargon; Truth Lab makes it interactive"),
    ("Differentiator", 5, 9, "Workbook + requirements only; Truth Lab NOT built yet"),
    ("AI process", 8, 9, "Two documented correction stories; tool list pending Samuel confirmation; screenshots/chat exports still missing"),
    ("Causality discipline", 10, 10, "No probability, no causal claim, scenarios labelled, pilot pre-registered"),
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    N = json.loads((OUT / "final_numbers.json").read_text(encoding="utf-8"))
    texts = {k: f.read_text(encoding="utf-8") for k, f in FILES.items()}
    reg = []
    for cid, desc, expected, where in claims(N):
        found = {w: (expected in texts[w]) for w in where}
        reg.append({"claim_id": cid, "claim": desc, "expected_text_from_final_numbers": expected, "required_in": ";".join(where),
                    "found_in": ";".join(w for w, ok in found.items() if ok), "status": "VERIFIED" if all(found.values()) else "NOT FOUND"})
    reg_df = pd.DataFrame(reg)
    stale = scan()
    wbc = pd.DataFrame(workbook_checks(N))
    score = pd.DataFrame(SCORECARD, columns=["criterion", "current_after_rewrite", "expected_after_truth_lab", "rationale"])
    reg_df.to_csv(OUT / "final_claims_register.csv", index=False)
    stale.to_csv(OUT / "stale_phrase_validation.csv", index=False)
    wbc.to_csv(OUT / "workbook_checks.csv", index=False)
    score.to_csv(OUT / "challenge_scorecard.csv", index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 120)
    print("claims:", reg_df.status.value_counts().to_dict())
    print(reg_df[reg_df.status != "VERIFIED"].to_string())
    print("stale scan:", stale.groupby(["status"]).size().to_dict())
    print(stale[stale.status == "MUST FIX"][["file", "line", "pattern", "reason", "text"]].to_string())
    print(wbc.to_string())
    print("score current:", score.current_after_rewrite.sum(), "expected after Truth Lab:", score.expected_after_truth_lab.sum())


if __name__ == "__main__":
    main()
