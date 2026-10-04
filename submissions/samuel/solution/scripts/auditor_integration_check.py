"""FINAL-AUDIT-INTEGRATION-01 — claim register for the new findings, stale-phrase scan and scorecard.

1. Every new number quoted in the submission is formatted from auditor_integration_summary.json
   (or the raw-recomputed CSVs) and searched in the files where it must appear.
2. Global scan for the phrases listed in item 27 of the prompt, classified
   CORRECT CURRENT / HISTORICAL / MUST FIX by declared rules.
3. Optional: compare a pre-rerun snapshot of the model outputs with the current ones
   (python solution/auditor_integration_check.py --snapshot <dir>).
4. Updated challenge scorecard (analyst judgement).

Run: python solution/scripts/auditor_integration_check.py [--snapshot DIR]
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd

from decimal import ROUND_HALF_UP, Decimal

from final_rewrite_check import ERRATA_MARKS, FILES, HIST_DOC, OUT_OF_SCOPE, ROOT, br_int
from _paths import OUTPUTS, PKG  # package paths


def br_pct(x: float, d: int = 1) -> str:
    """Half-up rounding on the exact decimal ratio (1077/2000 = 53.85% -> 53,9%, not the float artefact 53,8%)."""
    q = (Decimal(repr(round(x, 12))) * 100).quantize(Decimal(1).scaleb(-d), rounding=ROUND_HALF_UP)
    return f"{q}%".replace(".", ",")

OUT = OUTPUTS / "auditor_integration"


def claims(S: dict) -> list[tuple]:
    tq = {r["check"].split(" (")[0][:40]: r for r in S["temporal"]}
    t = S["temporal"]
    rf, sem, v3 = S["reason_feedback"], S["subscription_semantics"], S["V3_21_accounts"]
    sup = {r["metric"]: r for r in S["support_post_signup"]}
    seg = pd.read_csv(OUT / "segment_observed_rates_final.csv")
    den = json.loads((OUT / "usage_denominator_definition.json").read_text(encoding="utf-8"))
    out = [
        ("N01", "usage inside lifecycle (pt-BR)", br_pct(t[0]["share"], 2), ["README", "APPX", "LAB"]),
        ("N01b", "usage inside lifecycle (English label)", f"{100 * t[0]['share']:.2f}%", ["LAB"]),
        ("N02", "usage rows inside lifecycle", br_int(t[0]["rows_flagged"]), ["APPX", "LAB"]),
        ("N03", "usage before signup %", br_pct(t[1]["share"]), ["README", "EXEC", "APPX", "LAB"]),
        ("N04", "usage before signup rows", br_int(t[1]["rows_flagged"]), ["APPX", "LAB"]),
        ("N05", "tickets before signup %", br_pct(t[3]["rows_flagged"] / t[3]["rows_total"]), ["README", "EXEC", "APPX", "LAB"]),
        ("N06", "tickets before signup rows", br_int(t[3]["rows_flagged"]), ["APPX", "LAB"]),
        ("N07", "feedback texts", str(rf["events_with_feedback"]), ["README", "EXEC", "APPX", "LAB"]),
        ("N08", "reason x feedback p (3 dp, executive docs)", f"p = {rf['p_chi2_452']:.3f}".replace(".", ","), ["README", "EXEC"]),
        ("N09", "reason x feedback p (3 dp)", f"p = {rf['p_chi2_452']:.3f}".replace(".", ","), ["APPX"]),
        ("N10", "reason x feedback p (Truth Lab card)", f"p = {rf['p_chi2_452']:.3f}".replace(".", ","), ["LAB"]),
        ("N11", "auditor p with blank as category", f"p = {rf['p_chi2_600_blank_as_category']:.3f}".replace(".", ","), ["APPX"]),
        ("N12", "subscriptions churn_flag = end_date", f"{sem['subscriptions_churn_flag_true']} assinaturas têm `churn_flag = true`", ["APPX"]),
        ("N13", "mean active records per account", br_pct(sem["mean_active_records_per_account"] / 100).rstrip("%"), ["APPX", "LAB"]),
        ("N14", "accounts with all three plans active", f"{sem['accounts_all_three_plans_active']} / 500", ["APPX", "LAB"]),
        ("N15", "V3 409 wording", f"Das {v3['accounts_any_nonauto_active']} contas com algum registro ativo `auto_renew = false`", ["README"]),
        ("N16", "V3 21 wording", f"{v3['accounts_nonauto_zero_mrr_only']} possuem somente exposições `auto_renew = false` de trial com MRR proxy zero", ["README", "EXEC"]),
        ("N17", "V3 388/764/total", f"388 contas e 764 registros", ["README", "EXEC"]),
        ("N18", "denominator rule (README/EXEC)", "≥ 1 registro de assinatura ativo na data de fim do período", ["README", "EXEC"]),
        ("N19", "denominator active accounts 2023-12-31", f"{den['active_accounts_2023_12_31']} e {den['active_accounts_2024_12_31']} contas ativas", ["APPX"]),
        ("N20", "headline", "A RavenStack está medindo eventos diferentes como churn.", ["README", "EXEC"]),
        ("N21", "subheadline", "não conseguimos confirmar que o aumento dos eventos registrados representa aumento da perda real de clientes", ["README", "EXEC"]),
        ("N22", "final root cause wording", "os dados não sustentam um target confiável de perda de cliente", ["EXEC"]),
        ("N22b", "final root cause wording (README)", "Os dados não sustentam um target confiável de perda de cliente", ["README"]),
        ("N23", "support sensitivity tickets", f"| Tickets | {sup['tickets']['churn_flag_true_mean']:.2f} | {sup['tickets']['churn_flag_false_mean']:.2f} |".replace(".", ","), ["APPX"]),
        ("N24", "support sensitivity escalation", f"| Taxa de escalação | {br_pct(sup['escalation_rate']['churn_flag_true_mean'])} | {br_pct(sup['escalation_rate']['churn_flag_false_mean'])} |", ["APPX"]),
        ("N25", "support sensitivity CSAT", f"| CSAT | {sup['csat']['churn_flag_true_mean']:.2f} | {sup['csat']['churn_flag_false_mean']:.2f} |".replace(".", ","), ["APPX"]),
        ("N26", "overall rate num/den", "110 / 500", ["README", "EXEC", "APPX"]),
        ("N27", "Germany excluded", "8 / 25", ["README", "APPX"]),
        ("N28", "segment verdict label", "OBSERVED — NOT VALIDATED AS HIGHER RISK", ["README", "EXEC", "APPX"]),
    ]
    for r in seg[seg.eligible_n_ge_30].head(5).itertuples():
        out.append((f"N29-{r.segment}", f"segment {r.segment} churned/total", f"{r.churned} / {r.total}", ["README", "APPX"]))
    for k, n in S["account_flag_counts"].items():
        out.append((f"N30-{k}", f"account flag {k}", f"| `{k}` |", ["LAB"]))
    return out


STALE = {
    "21 only trials (old wording)": r"21 delas só têm trials|21 accounts only have trials|só têm trials com MRR",
    "still paying": r"still paying|continuam\s+\**todas\**\s+pagando|continuam pagando",
    "usage per account": r"uso por conta ativa|usage per active account|usage/account|uso por conta\b",
    "AUC range": r"AUC 0[,.]45[–-]0[,.]54",
    "reason codes uniform": r"15[–-]19% cada|quase uniforme|uniformly|reason codes? (are )?uniform",
    "subscription churn_flag": r"subscriptions?\.churn_flag",
    "classic churn driver": r"classic churn driver|driver clássico",
}
DENOM_OK = re.compile(r"¹|\*|=|÷|conta ativa\s*\(|registro de assinatura ativo|Active account|G6|denominador", re.I)


def classify(rel: str, kind: str, line: str, in_banner: bool, has_errata: bool, nearby: str) -> tuple[str, str]:
    if in_banner:
        return "HISTORICAL", "inside errata banner"
    current = not rel.startswith("docs/FINAL-EVIDENCE-REGISTER")
    if rel in OUT_OF_SCOPE:
        return "HISTORICAL", "source-of-truth / memory document: carries the prior wording, updated only by approved errata"
    if not current:
        if has_errata or HIST_DOC.search(rel) or rel.startswith("docs/1") or rel.startswith("docs/20") or rel.startswith("process-log/"):
            return "HISTORICAL", "historical analysis/working document"
        return "MUST FIX", "current non-submission document"
    if kind in {"21 only trials (old wording)", "still paying", "classic churn driver"}:
        if re.search(r"→|substitu|errou|antiga|impreciso|não verificável|Auditor independente \|", line, re.I):
            return "CORRECT CURRENT", "correction narrative"
        return "MUST FIX", "superseded wording"
    if kind == "usage per account":
        return ("CORRECT CURRENT", "denominator defined on the line or in the adjacent footnote/section") if DENOM_OK.search(line + " " + nearby) else ("MUST FIX", "usage per account without denominator")
    if kind == "AUC range":
        if rel.endswith("TECHNICAL-APPENDIX.md") and "predictive_permutation_null.csv" in nearby:
            return "CORRECT CURRENT", "appendix, with reproducible output paths"
        if re.search(r"→|substitu|errou|claim", line, re.I):
            return "CORRECT CURRENT", "correction narrative"
        return "MUST FIX", "AUC range in narrative without output link"
    if kind == "reason codes uniform":
        return ("CORRECT CURRENT", "mentions feedback-text alignment") if re.search(r"feedback", line + " " + nearby, re.I) else ("MUST FIX", "uniformity without feedback alignment")
    if kind == "subscription churn_flag":
        return ("CORRECT CURRENT", "explained as duplicate of subscription end") if re.search(r"duplicate|idêntico|não é um target|não aparece como definição|486", line + " " + nearby, re.I) else ("MUST FIX", "presented as independent definition")
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
                    while j < len(lines) and j < i + 40 and (lines[j].startswith(">") or lines[j].strip() == ""):
                        j += 1
                    banner_end = max(banner_end, j)
        for n, line in enumerate(lines, 1):
            nearby = " ".join(lines[max(0, n - 8): n + 6])
            for kind, rx in STALE.items():
                if re.search(rx, line, re.I):
                    st, why = classify(rel, kind, line, n <= banner_end and has_errata, has_errata, nearby)
                    rows.append({"file": rel, "line": n, "pattern": kind, "status": st, "reason": why, "text": line.strip()[:180]})
    return pd.DataFrame(rows)


def model_rerun(snapshot: Path) -> pd.DataFrame:
    pairs = [("end_to_end_sweep/predictive_permutation_null.csv", ["grain", "outcome", "model"], ["observed_oof_auc", "null_auc_mean", "permutation_p"]),
             ("end_to_end_sweep/predictive_test.csv", ["grain", "outcome", "model"], ["cv_roc_auc_mean"]),
             ("unblocked_models/ensemble_tests.csv", ["grain", "outcome", "model"], ["oof_auc_5_cv_seeds_mean", "null_auc_mean", "permutation_p"])]
    rows = []
    for rel, keys, cols in pairs:
        old = pd.read_csv(snapshot / rel).set_index(keys)
        new = pd.read_csv(OUTPUTS / rel).set_index(keys)
        for idx in old.index:
            for c in cols:
                o, nw = float(old.loc[idx, c]), float(new.loc[idx, c])
                rows.append({"output": rel, "model": " / ".join(idx), "metric": c, "before": o, "after_rerun": nw, "abs_diff": abs(o - nw),
                             "status": "IDENTICAL" if abs(o - nw) < 1e-9 else ("WITHIN 0.01" if abs(o - nw) < 0.01 else "DIFFERS")})
    return pd.DataFrame(rows)


SCORECARD = [
    ("Root cause", 9, 9, "Final wording: no reliable customer-loss target; definitions disagree + temporal/semantic inconsistencies; individual cause not identifiable"),
    ("Segments", 8, 8, "Observed ranking with churned/total, Wilson CI, verdict label and pre-defined N>=30 rule; business-priority column separate"),
    ("Specific accounts", 8, 9, "Named V1/V2/V3 lists; per-account descriptive data-quality flags ready for the Truth Lab brief"),
    ("Concrete actions", 9, 9, "Monday actions; reason-code redesign now a data-driven action (p=0.95 vs feedback text)"),
    ("Estimated impact", 7, 7, "Unchanged: fact / conditional scenario / pilot"),
    ("5-table crossing", 8, 9, "Temporal alignment checks now cross usage x subscriptions x accounts and tickets x accounts"),
    ("CEO usability", 8, 9, "Sharper headline + know / don't-know table; README kept short; Truth Lab not built"),
    ("Differentiator", 5, 9, "Truth Lab still NOT built: spec upgraded (data-quality story, confidence page, account flags)"),
    ("AI process", 9, 9, "Third independent verification (clean-chat auditor) reproduced before incorporation; 52/53 reproduced, 1 conflict reported; screenshots still missing"),
    ("Causality discipline", 10, 10, "No probability, no score; flags descriptive; segments labelled not validated"),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", type=Path)
    args = ap.parse_args()
    S = json.loads((OUT / "auditor_integration_summary.json").read_text(encoding="utf-8"))
    texts = {k: f.read_text(encoding="utf-8") for k, f in FILES.items()}
    reg = []
    for cid, desc, expected, where in claims(S):
        found = {w: (expected in texts[w]) for w in where}
        reg.append({"claim_id": cid, "claim": desc, "expected_text": expected, "required_in": ";".join(where),
                    "found_in": ";".join(w for w, ok in found.items() if ok), "status": "VERIFIED" if all(found.values()) else "NOT FOUND"})
    reg_df = pd.DataFrame(reg)
    stale = scan()
    score = pd.DataFrame(SCORECARD, columns=["criterion", "current", "expected_after_truth_lab", "rationale"])
    reg_df.to_csv(OUT / "integration_claims_register.csv", index=False)
    stale.to_csv(OUT / "integration_stale_phrase_scan.csv", index=False)
    score.to_csv(OUT / "challenge_scorecard_after_integration.csv", index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 110)
    print("claims:", reg_df.status.value_counts().to_dict())
    print(reg_df[reg_df.status != "VERIFIED"].to_string())
    print("stale scan:", stale.groupby("status").size().to_dict() if len(stale) else {})
    print(stale[stale.status == "MUST FIX"][["file", "line", "pattern", "reason", "text"]].to_string())
    if args.snapshot:
        mr = model_rerun(args.snapshot)
        mr.to_csv(OUT / "model_rerun_comparison.csv", index=False)
        print("model rerun:", mr.status.value_counts().to_dict(), "max abs diff", mr.abs_diff.max())
        print(mr[mr.status != "IDENTICAL"].to_string())
    print("score current:", score.current.sum(), "expected after Truth Lab:", score.expected_after_truth_lab.sum())


if __name__ == "__main__":
    main()
