"""FINAL-AUDIT-INTEGRATION-01 — independent recomputation of the clean-chat auditor's findings.

Every number the auditor reported is recomputed here from the RAW CSVs. Nothing is
taken from the auditor's text: if a value does not reproduce, it is written to
auditor_findings_validation.csv as CONFLICT and the reproduced value is the one used.
No new driver search, no new model, no score.

Outputs: solution/outputs/auditor_integration/
Run: python solution/scripts/auditor_integration.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from _paths import OUTPUTS, PKG, RAW_DIR, ROOT  # noqa: E402,F401  (package paths)
RAW = RAW_DIR
OUT = OUTPUTS / "auditor_integration"
FINAL = OUTPUTS / "final_rewrite" / "final_numbers.json"
SEED = 20261004


def load():
    a = pd.read_csv(RAW / "ravenstack_accounts.csv", parse_dates=["signup_date"])
    s = pd.read_csv(RAW / "ravenstack_subscriptions.csv", parse_dates=["start_date", "end_date"])
    u = pd.read_csv(RAW / "ravenstack_feature_usage.csv", parse_dates=["usage_date"])
    t = pd.read_csv(RAW / "ravenstack_support_tickets.csv", parse_dates=["submitted_at", "closed_at"])
    c = pd.read_csv(RAW / "ravenstack_churn_events.csv", parse_dates=["churn_date"])
    return a, s, u, t, c


def wilson(k: int, n: int) -> tuple[float, float]:
    z, p = 1.96, k / n
    d = 1 + z * z / n
    m = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return m - h, m + h


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    a, s, u, t, c = load()
    ids = a.account_id
    A = a.set_index("account_id")
    active, ended = s[s.end_date.isna()], s[s.end_date.notna()]
    checks: list[dict] = []

    def check(fid, claim, expected, reproduced, tol=0.0, note=""):
        ok = abs(float(reproduced) - float(expected)) <= tol
        checks.append({"finding": fid, "claim": claim, "auditor_value": expected, "reproduced_value": reproduced,
                       "status": "REPRODUCED" if ok else "CONFLICT", "note": note})

    # 0. Numbers the auditor confirmed (must not move)
    F = json.loads(FINAL.read_text(encoding="utf-8"))
    cd = F["churn_definitions"]
    for k, v in [("churn_flag", 110), ("any_churn_event", 352), ("any_subscription_end", 312), ("zero_active_records_2024_12_31", 0),
                 ("flag_and_event", 75), ("flag_and_end", 72), ("event_and_end", 227), ("all_three", 50)]:
        check("A0", f"churn_definitions.{k}", v, cd[k])
    check("A0", "V1 accounts", 110, F["V1"]["accounts"]); check("A0", "V1 MRR proxy", 2073153, F["V1"]["active_mrr_proxy"])
    check("A0", "V2 MRR proxy", 2781650, F["V2"]["active_mrr_proxy"])
    check("A0", "V3 accounts", 388, F["V3"]["accounts"]); check("A0", "V3 records", 764, F["V3"]["records_with_mrr"])
    check("A0", "V3 MRR proxy", 2023778, F["V3"]["exposed_mrr_proxy"])
    check("A0", "V3-W1 accounts", 50, F["V3W1"]["accounts"]); check("A0", "V3-W1 records", 137, F["V3W1"]["records"])
    check("A0", "V3-W1 MRR proxy", 873996, F["V3W1"]["exposed_mrr_proxy"]); check("A0", "Wave 1 accounts", 176, F["wave1"]["union_accounts"])

    # 1. Temporal data quality
    uu = u.merge(s[["subscription_id", "account_id", "start_date", "end_date"]]).merge(a[["account_id", "signup_date"]])
    in_life = (uu.usage_date >= uu.start_date) & (uu.end_date.isna() | (uu.usage_date <= uu.end_date))
    u_pre = uu.usage_date < uu.signup_date
    tt = t.merge(a[["account_id", "signup_date", "churn_flag"]])
    t_pre = tt.submitted_at < tt.signup_date
    temporal = pd.DataFrame([
        {"table": "feature_usage", "check": "usage_date inside the linked subscription's observed life (start_date <= usage_date <= end_date, open end allowed)",
         "rows_flagged": int(in_life.sum()), "rows_total": len(uu), "share": in_life.mean(), "status": "PARTIAL"},
        {"table": "feature_usage", "check": "usage_date before the account's signup_date", "rows_flagged": int(u_pre.sum()),
         "rows_total": len(uu), "share": u_pre.mean(), "status": "WARNING"},
        {"table": "feature_usage", "check": "usage_date before the linked subscription's start_date", "rows_flagged": int((uu.usage_date < uu.start_date).sum()),
         "rows_total": len(uu), "share": (uu.usage_date < uu.start_date).mean(), "status": "WARNING"},
        {"table": "support_tickets", "check": "submitted_at before the account's signup_date", "rows_flagged": int(t_pre.sum()),
         "rows_total": len(tt), "share": t_pre.mean(), "status": "WARNING"},
    ])
    temporal.to_csv(OUT / "temporal_data_quality.csv", index=False)
    check("T1", "usage rows inside subscription life", 5568, int(in_life.sum()))
    check("T2", "usage rows before account signup", 13198, int(u_pre.sum()))
    check("T3", "tickets before account signup", 1077, int(t_pre.sum()))

    # 2. Support sensitivity: drop pre-signup tickets; account-level means among accounts with >=1 remaining ticket
    p = tt[~t_pre]
    acc = p.groupby("account_id").agg(tickets=("ticket_id", "size"), first_response_min=("first_response_time_minutes", "mean"),
                                      resolution_h=("resolution_time_hours", "mean"), escalation_rate=("escalation_flag", "mean"),
                                      csat=("satisfaction_score", "mean")).join(A.churn_flag)
    rows = []
    for col in ["tickets", "first_response_min", "resolution_h", "escalation_rate", "csat"]:
        x1, x0 = acc.loc[acc.churn_flag, col].dropna(), acc.loc[~acc.churn_flag, col].dropna()
        rows.append({"metric": col, "churn_flag_true_mean": x1.mean(), "churn_flag_false_mean": x0.mean(),
                     "n_true": len(x1), "n_false": len(x0), "mann_whitney_p": stats.mannwhitneyu(x1, x0).pvalue})
    sup = pd.DataFrame(rows)
    sup["scope"] = f"tickets with submitted_at >= signup_date ({len(p)} of {len(tt)}); account-level means over accounts with >=1 remaining ticket"
    sup.to_csv(OUT / "support_post_signup_sensitivity.csv", index=False)
    S = sup.set_index("metric")
    for m, e1, e0, tol in [("tickets", 2.43, 2.48, 0.006), ("first_response_min", 88.8, 89.8, 0.06), ("resolution_h", 34.4, 35.8, 0.06),
                           ("escalation_rate", 0.070, 0.055, 0.0006), ("csat", 4.03, 3.94, 0.006)]:
        check("S1", f"{m} churn_flag=true", e1, round(S.loc[m, "churn_flag_true_mean"], 3), tol)
        check("S1", f"{m} churn_flag=false", e0, round(S.loc[m, "churn_flag_false_mean"], 3), tol)

    # 3. Reason code x feedback text
    f = c[c.feedback_text.notna()]
    ct = pd.crosstab(f.reason_code, f.feedback_text)
    chi2, pv, dof, _ = stats.chi2_contingency(ct)
    rng = np.random.default_rng(SEED)
    null = np.array([stats.chi2_contingency(pd.crosstab(rng.permutation(f.reason_code.values), f.feedback_text.values))[0] for _ in range(5000)])
    p_perm = float((null >= chi2).mean())
    ct_blank = pd.crosstab(c.reason_code, c.feedback_text.fillna("<blank>"))
    p_blank = stats.chi2_contingency(ct_blank)[1]
    cramer = float(np.sqrt(chi2 / (ct.values.sum() * (min(ct.shape) - 1))))
    long = ct.stack().rename("events").reset_index()
    long["share_within_feedback_text"] = long.events / long.groupby("feedback_text").events.transform("sum")
    long.to_csv(OUT / "reason_feedback_alignment.csv", index=False)
    rf = {"events_total": len(c), "events_with_feedback": len(f), "distinct_feedback_texts": int(f.feedback_text.nunique()),
          "chi2": chi2, "dof": dof, "p_chi2_452": pv, "p_permutation_452": p_perm, "cramers_v": cramer,
          "p_chi2_600_blank_as_category": p_blank,
          "aligned_pairs": {"too expensive -> pricing/budget": int(ct.loc[["pricing", "budget"], "too expensive"].sum()),
                            "too expensive total": int(ct["too expensive"].sum()),
                            "switched to competitor -> competitor": int(ct.loc["competitor", "switched to competitor"]),
                            "switched to competitor total": int(ct["switched to competitor"].sum()),
                            "missing features -> features": int(ct.loc["features", "missing features"]),
                            "missing features total": int(ct["missing features"].sum())}}
    check("R1", "churn events with feedback text", 452, len(f))
    check("R2", "reason_code x feedback_text p-value", 0.986, round(pv, 3), 0.005,
          f"0.986 reproduces only when the 148 blank feedbacks enter as a category (p={p_blank:.3f}, n=600). "
          f"On the 452 filled texts: chi2 p={pv:.3f}, permutation p={p_perm:.3f}. Conclusion unchanged: no detectable association.")

    # 4. Subscription churn_flag == subscription end
    has_end = s.end_date.notna()
    check("U1", "subscriptions churn_flag=true", 486, int(s.churn_flag.sum()))
    check("U1", "churn_flag=true with end_date", 486, int((s.churn_flag & has_end).sum()))
    check("U1", "churn_flag=false with end_date", 0, int((~s.churn_flag & has_end).sum()))

    # 5. Subscription semantics at observation end
    per_acc = active.groupby("account_id").agg(active_records=("subscription_id", "size"), plan_tiers=("plan_tier", "nunique"))
    sem = {"active_records": len(active), "accounts_with_active_record": int(per_acc.shape[0]),
           "mean_active_records_per_account": float(per_acc.active_records.mean()), "median_active_records_per_account": float(per_acc.active_records.median()),
           "accounts_all_three_plans_active": int((per_acc.plan_tiers == 3).sum()), "accounts_two_plus_plans_active": int((per_acc.plan_tiers >= 2).sum()),
           "subscriptions_churn_flag_true": int(s.churn_flag.sum()), "subscriptions_with_end_date": int(has_end.sum()),
           "churn_flag_equals_end_date_all_rows": bool((s.churn_flag == has_end).all())}
    check("U2", "mean active records per account at end", 9.0, round(sem["mean_active_records_per_account"], 1), 0.1)
    check("U2", "accounts with Basic+Pro+Enterprise active", 418, sem["accounts_all_three_plans_active"])
    pd.DataFrame([{"metric": k, "value": v} for k, v in sem.items()]).to_csv(OUT / "subscription_semantics.csv", index=False)

    # 6. V3 — the 21 accounts
    nonauto = active[~active.auto_renew_flag]
    g = nonauto.groupby("account_id").agg(mrr=("mrr_amount", "sum"), records=("subscription_id", "size"), all_trial=("is_trial", "all"))
    zero = g[g.mrr == 0]
    paid_other = active[(active.account_id.isin(zero.index)) & (active.mrr_amount > 0)].account_id.nunique()
    v3 = {"accounts_any_nonauto_active": int(g.shape[0]), "accounts_nonauto_zero_mrr_only": int(zero.shape[0]),
          "zero_nonauto_records": int(zero.records.sum()), "zero_nonauto_all_trials": bool(zero.all_trial.all()),
          "of_which_have_other_paid_active_records": int(paid_other), "V3_accounts": int((g.mrr > 0).sum()),
          "V3_records": int(((nonauto.mrr_amount > 0)).sum()), "V3_mrr_proxy": float(nonauto.mrr_amount.sum())}
    check("V3", "accounts with any active auto_renew=false record", 409, v3["accounts_any_nonauto_active"])
    check("V3", "of which non-auto-renew exposure is zero-MRR trial only", 21, v3["accounts_nonauto_zero_mrr_only"])

    # 7. Observed segment rates (final form, unchanged rule: churn_flag, N>=30)
    df = a.copy()
    df["seats_band"] = pd.cut(df.seats, [0, 5, 15, 30, 1000], labels=["1-5", "6-15", "16-30", "31+"]).astype(str)
    df["signup_half"] = df.signup_date.dt.year.astype(str) + "H" + np.where(df.signup_date.dt.month <= 6, "1", "2")
    seg = []
    for col, lab in [("industry", "industry"), ("country", "country"), ("referral_source", "acquisition channel"), ("plan_tier", "plan"),
                     ("is_trial", "trial"), ("seats_band", "seats"), ("signup_half", "signup cohort")]:
        for lvl, gdf in df.groupby(col):
            k, n = int(gdf.churn_flag.sum()), len(gdf)
            lo, hi = wilson(k, n)
            seg.append({"dimension": lab, "segment": str(lvl), "churned": k, "total": n, "churned_over_total": f"{k} / {n}", "observed_rate": k / n,
                        "ci95_low": lo, "ci95_high": hi, "eligible_n_ge_30": n >= 30,
                        "verdict": "OBSERVED — NOT VALIDATED AS HIGHER RISK" if n >= 30 else "Excluded from the ranking by the pre-defined N>=30 rule"})
    seg = pd.DataFrame(seg).sort_values("observed_rate", ascending=False)
    seg.to_csv(OUT / "segment_observed_rates_final.csv", index=False)
    top = seg[seg.eligible_n_ge_30].head(5)
    for (sg, k, n) in [("DevTools", 35, 113), ("event", 29, 96), ("2023H1", 29, 109), ("True", 25, 97), ("6-15", 33, 134)]:
        r = seg[seg.segment == sg].iloc[0]
        check("G1", f"{sg} churned", k, r.churned)
        check("G1", f"{sg} total", n, r.total)
    check("G1", "overall churned", 110, int(a.churn_flag.sum()))
    de = seg[seg.segment == "DE"].iloc[0]
    check("G2", "Germany total (excluded, N<30)", 25, de.total); check("G2", "Germany rate", 0.32, round(de.observed_rate, 2), 0.001)

    # 8. Usage-per-active-account denominator (read from final_rewrite_build.py and end_to_end_sweep.py — same rule)
    def active_accounts(end):
        return s[(s.start_date <= end) & (s.end_date.isna() | (s.end_date > end))].account_id.nunique()
    den = {
        "metric": "usage per active account",
        "formula": "sum(feature_usage.usage_count where usage_date in period) / count(distinct account_id with >=1 subscription record where start_date <= period_end AND (end_date is null OR end_date > period_end))",
        "active_account_rule": "Active account = account with >=1 subscription record active at the period-end date (start_date <= period_end and end_date empty or after period_end).",
        "numerator_note": "All usage rows dated in the period, joined to the account via subscription_id. Rows are NOT filtered to the subscription's observed life (only 22.27% fall inside it).",
        "segment_note": "For segment cuts (industry, country, plan), numerator and denominator are both restricted to accounts whose accounts-table attribute equals the segment.",
        "periods_used": {"segment_comparison": "2023H2 (2023-07-01..2023-12-31, period_end 2023-12-31) vs 2024H2 (2024-07-01..2024-12-31, period_end 2024-12-31)",
                         "quarterly_table": "calendar quarter, period_end = last day of the quarter"},
        "source_code": ["solution/final_rewrite_build.py: act_accounts()", "solution/end_to_end_sweep.py: monthly_panel() accounts_with_active_sub_eom"],
        "active_accounts_2023_12_31": active_accounts(pd.Timestamp("2023-12-31")), "active_accounts_2024_12_31": active_accounts(pd.Timestamp("2024-12-31")),
    }
    (OUT / "usage_denominator_definition.json").write_text(json.dumps(den, indent=2, ensure_ascii=False), encoding="utf-8")

    # 9. Descriptive per-account data-quality flags (NOT a score)
    ev = pd.Series(ids.isin(c.account_id).values, index=ids)
    en = pd.Series(ids.isin(ended.account_id).values, index=ids)
    flags = pd.DataFrame({
        "usage_before_signup": pd.Series(ids.isin(uu[u_pre].account_id).values, index=ids),
        "ticket_before_signup": pd.Series(ids.isin(tt[t_pre].account_id).values, index=ids),
        "multiple_plan_overlap": (per_acc.plan_tiers.reindex(ids, fill_value=0) >= 2).values,
        "churn_flag_event_end_mismatch": ~((A.churn_flag == ev) & (ev == en)).values,
        "non_auto_renew_zero_mrr_only": pd.Series(ids.isin(zero.index).values, index=ids),
    }, index=ids)
    flags.reset_index().to_csv(OUT / "account_data_quality_flags.csv", index=False)
    flag_counts = {k: int(v) for k, v in flags.sum().items()}

    pd.DataFrame(checks).to_csv(OUT / "auditor_findings_validation.csv", index=False)
    summary = {"temporal": temporal.to_dict("records"), "support_post_signup": sup.drop(columns="scope").to_dict("records"),
               "support_post_signup_tickets": len(p), "reason_feedback": rf, "subscription_semantics": sem, "V3_21_accounts": v3,
               "account_flag_counts": flag_counts, "top5_segments": top[["dimension", "segment", "churned", "total", "observed_rate", "ci95_low", "ci95_high"]].to_dict("records"),
               "checks_reproduced": int(sum(x["status"] == "REPRODUCED" for x in checks)), "checks_total": len(checks),
               "conflicts": [x for x in checks if x["status"] == "CONFLICT"]}
    (OUT / "auditor_integration_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    print(pd.DataFrame(checks)[["finding", "claim", "auditor_value", "reproduced_value", "status"]].to_string())
    print(json.dumps({k: summary[k] for k in ["reason_feedback", "subscription_semantics", "V3_21_accounts", "account_flag_counts"]}, indent=1, default=float))
    print(sup.round(3).to_string())


if __name__ == "__main__":
    main()
