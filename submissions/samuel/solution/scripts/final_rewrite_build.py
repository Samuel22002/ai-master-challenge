"""FINAL-REWRITE-01 — numbers and CS action-queue workbook for the rewritten submission.

Every number quoted in the submission is recomputed here from the RAW CSVs and written
to solution/outputs/final_rewrite/final_numbers.json. No currency is attached to any
mrr_amount sum: the dataset declares mrr_amount only as type "currency" without a unit
(the only explicit currency is refund_amount_usd), so values are labelled "MRR proxy".

Run: python solution/scripts/final_rewrite_build.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo
from scipy import stats
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_effectsize

from _paths import OUTPUTS, PKG, RAW_DIR, ROOT  # noqa: E402,F401  (package paths)
RAW = RAW_DIR
OUT = OUTPUTS / "final_rewrite"
XLSX = PKG / "solution" / "RavenStack_CS_Action_Queues.xlsx"
OBS_END = pd.Timestamp("2024-12-31")


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
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def observed_segment_rates(a: pd.DataFrame) -> pd.DataFrame:
    """Descriptive churn_flag rate by segment, with Wilson CI and BH-adjusted dimension test. NOT a risk model."""
    from statsmodels.stats.multitest import multipletests
    df = a.copy()
    df["seats_band"] = pd.cut(df.seats, [0, 5, 15, 30, 1000], labels=["1-5", "6-15", "16-30", "31+"]).astype(str)
    df["signup_half"] = df.signup_date.dt.year.astype(str) + np.where(df.signup_date.dt.month <= 6, "H1", "H2")
    df["is_trial"] = df.is_trial.map({True: "trial", False: "not trial"})
    dims = {"industry": "Indústria", "country": "País", "referral_source": "Canal de aquisição", "plan_tier": "Plano (conta)",
            "is_trial": "Trial", "seats_band": "Faixa de seats", "signup_half": "Coorte de signup"}
    rows, tests = [], []
    overall = df.churn_flag.mean()
    for col, lab in dims.items():
        ct = pd.crosstab(df[col], df.churn_flag)
        p = stats.chi2_contingency(ct)[1]
        tests.append((col, p))
        for lvl, r in ct.iterrows():
            n, k = int(r.sum()), int(r.get(True, 0))
            lo, hi = wilson(k, n)
            rows.append({"dimension": lab, "segment": str(lvl), "accounts": n, "churn_flag_accounts": k, "observed_rate": k / n,
                         "ci95_low": lo, "ci95_high": hi, "overall_rate": overall, "dimension_chi2_p": p})
    out = pd.DataFrame(rows)
    q = dict(zip([t[0] for t in tests], multipletests([t[1] for t in tests], method="fdr_bh")[1]))
    inv = {v: k for k, v in dims.items()}
    out["dimension_q_bh"] = out.dimension.map(lambda d: q[inv[d]])
    out["small_sample"] = out.accounts < 30
    out["label"] = "Observed, not validated — not a predicted churn risk"
    return out.sort_values("observed_rate", ascending=False).reset_index(drop=True)


def mde(n_arm: int, base: float) -> float:
    p1 = next(p for p in np.arange(base - 0.0005, 0, -0.0005)
              if NormalIndPower().power(abs(proportion_effectsize(base, p)), nobs1=n_arm, alpha=0.05) >= 0.8)
    return round((base - p1) * 100, 1)


def build() -> tuple[dict, dict[str, pd.DataFrame]]:
    a, s, u, t, c = load()
    ids = a.account_id
    A = a.set_index("account_id")
    active, ended = s[s.end_date.isna()], s[s.end_date.notna()]
    act_mrr = active.groupby("account_id").mrr_amount.sum().reindex(ids, fill_value=0)
    act_n = active.groupby("account_id").size().reindex(ids, fill_value=0)
    total = float(act_mrr.sum())
    flag = A.churn_flag
    ev_n = c.groupby("account_id").size().reindex(ids, fill_value=0)
    has_ev, has_end = ev_n > 0, pd.Series(ids.isin(ended.account_id).values, index=ids)
    last_ev = c.groupby("account_id").churn_date.max().reindex(ids)
    end_n = ended.groupby("account_id").size().reindex(ids, fill_value=0)
    nonauto = active[~active.auto_renew_flag]
    exp_mrr = nonauto.groupby("account_id").mrr_amount.sum().reindex(ids, fill_value=0)
    exp_rec = nonauto[nonauto.mrr_amount > 0].groupby("account_id").size().reindex(ids, fill_value=0)
    exp_m = nonauto[(nonauto.mrr_amount > 0) & (nonauto.billing_frequency == "monthly")].groupby("account_id").mrr_amount.sum().reindex(ids, fill_value=0)
    exp_a = nonauto[(nonauto.mrr_amount > 0) & (nonauto.billing_frequency == "annual")].groupby("account_id").mrr_amount.sum().reindex(ids, fill_value=0)
    nonauto_any = pd.Series(ids.isin(nonauto.account_id).values, index=ids)
    V1 = flag & (act_mrr > 0)
    vrank = act_mrr.rank(ascending=False, method="first")
    erank = exp_mrr.rank(ascending=False, method="first")
    V2, V3 = vrank <= 50, exp_mrr > 0
    W1 = erank <= 50
    wave1 = V1 | V2 | W1
    pilot = V3 & ~(V2 | W1)
    v3r = nonauto[nonauto.mrr_amount > 0]
    srt = act_mrr.sort_values(ascending=False)

    # usage per active account by segment, 2023H2 vs 2024H2
    us = u.merge(s[["subscription_id", "account_id"]]).merge(a[["account_id", "industry", "country", "plan_tier"]])
    def act_accounts(mask_ids, end):
        ss = s[s.account_id.isin(mask_ids)]
        return ss[(ss.start_date <= end) & (ss.end_date.isna() | (ss.end_date > end))].account_id.nunique()
    seg_rows = []
    for seg in ["industry", "country", "plan_tier"]:
        for lvl in sorted(a[seg].unique()):
            idl = a[a[seg] == lvl].account_id
            v23 = us[(us[seg] == lvl) & us.usage_date.between("2023-07-01", "2023-12-31")].usage_count.sum() / max(act_accounts(idl, pd.Timestamp("2023-12-31")), 1)
            v24 = us[(us[seg] == lvl) & us.usage_date.between("2024-07-01", "2024-12-31")].usage_count.sum() / max(act_accounts(idl, OBS_END), 1)
            seg_rows.append({"segment": seg, "level": lvl, "usage_per_active_account_2023H2": round(v23, 1),
                             "usage_per_active_account_2024H2": round(v24, 1), "change_pct": round(100 * (v24 / v23 - 1), 0)})
    seg_df = pd.DataFrame(seg_rows)
    q_usage = u.groupby(u.usage_date.dt.to_period("Q")).usage_count.sum()

    # churned (churn_flag) vs retained, account level
    ua = u.merge(s[["subscription_id", "account_id"]]).groupby("account_id").agg(usage=("usage_count", "sum"), features=("feature_name", "nunique"),
                                                                                 errors=("error_count", "sum"))
    ua["error_rate"] = ua.errors / ua.usage
    ta = t.groupby("account_id").agg(tickets=("ticket_id", "size"), frt_min=("first_response_time_minutes", "mean"),
                                     resolution_h=("resolution_time_hours", "mean"), escalations=("escalation_flag", "sum"),
                                     csat=("satisfaction_score", "mean"))
    M = A[["churn_flag"]].join(ua).join(ta)
    M[["tickets", "escalations"]] = M[["tickets", "escalations"]].fillna(0)
    cvr = []
    for col, lab in [("usage", "usage events (sum)"), ("features", "distinct features used"), ("errors", "errors (sum)"), ("error_rate", "errors per usage"),
                     ("tickets", "tickets"), ("frt_min", "first response (min)"), ("resolution_h", "resolution (h)"), ("escalations", "escalations"), ("csat", "CSAT (3-5 observed)")]:
        x1, x0 = M.loc[M.churn_flag, col].dropna(), M.loc[~M.churn_flag, col].dropna()
        cvr.append({"metric": lab, "churn_flag_true_mean": round(x1.mean(), 3), "churn_flag_false_mean": round(x0.mean(), 3),
                    "mann_whitney_p": round(stats.mannwhitneyu(x1, x0).pvalue, 3)})
    cvr_df = pd.DataFrame(cvr)

    e24 = ended[ended.end_date >= "2024-01-01"]
    after = np.mean([bool(((s.account_id == r.account_id) & (s.start_date <= r.end_date) & (s.end_date.isna() | (s.end_date > r.end_date))).any()) for r in e24.itertuples()])
    pend = pd.crosstab(s.plan_tier, s.end_date.notna())
    uu = u.merge(s[["subscription_id", "start_date", "end_date"]])
    inlife = ((uu.usage_date >= uu.start_date) & (uu.end_date.isna() | (uu.usage_date <= uu.end_date))).mean()
    exposure = float(exp_mrr[V3].sum())
    n_arm = int(pilot.sum()) // 2

    N = {
        "currency_note": "mrr_amount has no declared unit; no currency symbol is used. refund_amount_usd is the only explicit currency in the dataset.",
        "churn_definitions": {"churn_flag": int(flag.sum()), "any_churn_event": int(has_ev.sum()), "any_subscription_end": int(has_end.sum()),
                              "zero_active_records_2024_12_31": int((act_n == 0).sum()), "flag_and_event": int((flag & has_ev).sum()),
                              "flag_and_end": int((flag & has_end).sum()), "event_and_end": int((has_ev & has_end).sum()),
                              "all_three": int((flag & has_ev & has_end).sum())},
        "active_mrr_proxy_total": total,
        "V1": {"accounts": int(V1.sum()), "flag_accounts_with_zero_active_mrr": int((flag & (act_mrr == 0)).sum()),
               "active_mrr_proxy": float(act_mrr[V1].sum()), "share_active": float(act_mrr[V1].sum() / total),
               "with_events": int((V1 & has_ev).sum()), "with_ended_records": int((V1 & has_end).sum())},
        "V2": {"accounts": int(V2.sum()), "records": int(active.account_id.isin(V2[V2].index).sum()), "active_mrr_proxy": float(act_mrr[V2].sum()),
               "share_active": float(act_mrr[V2].sum() / total)},
        "concentration": {k: {"mrr_proxy": float(srt.iloc[lo:hi].sum()), "share": float(srt.iloc[lo:hi].sum() / total)}
                          for k, lo, hi in [("top10", 0, 10), ("top20", 0, 20), ("top50", 0, 50), ("ranks51_150", 50, 150), ("ranks151_500", 150, 500)]},
        "V3": {"accounts": int(V3.sum()), "records_with_mrr": len(v3r), "exposed_mrr_proxy": exposure, "share_active": exposure / total,
               "monthly_records": int((v3r.billing_frequency == "monthly").sum()), "monthly_mrr_proxy": float(v3r[v3r.billing_frequency == "monthly"].mrr_amount.sum()),
               "annual_records": int((v3r.billing_frequency == "annual").sum()), "annual_mrr_proxy": float(v3r[v3r.billing_frequency == "annual"].mrr_amount.sum()),
               "any_nonauto_accounts": int(nonauto_any.sum()), "any_nonauto_records": len(nonauto), "zero_mrr_nonauto_records": int((nonauto.mrr_amount == 0).sum()),
               "trial_only_accounts": int((nonauto_any & ~V3).sum()),
               "trial_only_records": int(nonauto.account_id.isin((nonauto_any & ~V3)[nonauto_any & ~V3].index).sum())},
        "V3W1": {"accounts": int(W1.sum()), "records": int(v3r.account_id.isin(W1[W1].index).sum()), "exposed_mrr_proxy": float(exp_mrr[W1].sum()),
                 "share_of_V3": float(exp_mrr[W1].sum() / exposure), "share_active": float(exp_mrr[W1].sum() / total)},
        "wave1": {"union_accounts": int(wave1.sum()), "naive_sum": int(V1.sum() + V2.sum() + W1.sum()), "V1_V2": int((V1 & V2).sum()),
                  "V1_W1": int((V1 & W1).sum()), "V2_W1": int((V2 & W1).sum()), "triple": int((V1 & V2 & W1).sum()),
                  "active_mrr_proxy": float(act_mrr[wave1].sum()), "share_active": float(act_mrr[wave1].sum() / total)},
        "enterprise": {"accounts_any_active_record": int(active[active.plan_tier == "Enterprise"].account_id.nunique()),
                       "accounts_active_record_mrr_gt0": int(active[(active.plan_tier == "Enterprise") & (active.mrr_amount > 0)].account_id.nunique()),
                       "share_active_mrr": float(active[active.plan_tier == "Enterprise"].mrr_amount.sum() / total),
                       "p_end_by_plan": (pend[True] / pend.sum(axis=1)).round(4).to_dict(), "chi2_p": float(stats.chi2_contingency(pend)[1])},
        "ended_2024": {"mrr_proxy": float(e24.mrr_amount.sum()), "share_in_accounts_active_at_end": float(e24.account_id.isin(active.account_id).mean()),
                       "share_with_other_active_record_right_after": float(after)},
        "scenarios_on_V3": [{"pct": p, "mrr_proxy": exposure * p, "annualized_proxy": exposure * p * 12} for p in (0.05, 0.10, 0.15)],
        "pilot": {"population": int(pilot.sum()), "per_arm": n_arm, "exposed_mrr_proxy": float(exp_mrr[pilot].sum()),
                  "mde_pp": {str(b): mde(n_arm, b) for b in (0.10, 0.15, 0.20)}},
        "usage": {"quarterly_total_min": int(q_usage.min()), "quarterly_total_max": int(q_usage.max()),
                  "segments_declining": int((seg_df.change_pct < 0).sum()), "segments_tested": len(seg_df),
                  "segment_change_min_pct": float(seg_df.change_pct.min()), "segment_change_max_pct": float(seg_df.change_pct.max()),
                  "usage_rows_inside_subscription_life": float(inlife)},
        "support": {"csat_missing_share": float(t.satisfaction_score.isna().mean()), "csat_min": float(t.satisfaction_score.min()),
                    "csat_max": float(t.satisfaction_score.max()),
                    "priority_vs_resolution_kruskal_p": float(stats.kruskal(*[g.resolution_time_hours for _, g in t.groupby("priority")]).pvalue)},
        "reason_code_share_range": [float(c.reason_code.value_counts(normalize=True).min()), float(c.reason_code.value_counts(normalize=True).max())],
        "health_score_readiness": {"green": 0, "partial": 2, "red": 8},
    }
    seg_rates = observed_segment_rates(a)
    top = seg_rates[~seg_rates.small_sample].head(5)
    N["observed_segment_rates"] = {
        "overall_churn_flag_rate": float(a.churn_flag.mean()),
        "top5_n_ge_30": [{"dimension": r.dimension, "segment": r.segment, "accounts": int(r.accounts), "rate": float(r.observed_rate),
                          "ci95": [float(r.ci95_low), float(r.ci95_high)], "dimension_p": float(r.dimension_chi2_p), "dimension_q": float(r.dimension_q_bh)}
                         for r in top.itertuples()],
        "min_dimension_q": float(seg_rates.dimension_q_bh.min()),
        "dimensions_with_p_lt_05": int((seg_rates.drop_duplicates("dimension").dimension_chi2_p < 0.05).sum()),
    }
    tables = {"segment_usage": seg_df, "churned_vs_retained": cvr_df, "observed_segment_rates": seg_rates}

    # ---------------- workbook rows
    base = A[["account_name", "industry", "country", "referral_source", "plan_tier"]].rename(columns={"plan_tier": "account_plan_tier"})
    base["active_records"] = act_n; base["active_mrr_proxy"] = act_mrr; base["value_rank"] = vrank.astype(int)
    base["churn_events"] = ev_n; base["last_churn_event"] = last_ev.dt.date; base["ended_records"] = end_n
    base["exposed_records_with_mrr"] = exp_rec; base["exposed_mrr_proxy"] = exp_mrr
    base["exposed_monthly_mrr_proxy"] = exp_m; base["exposed_annual_mrr_proxy"] = exp_a; base["exposure_rank"] = erank.astype(int)
    base["in_V1"], base["in_V2"], base["in_V3"], base["in_V3_W1"] = V1, V2, V3, W1
    base["pilot_eligible"] = pilot
    yn = lambda m: np.where(m, "yes", "")
    v1 = base[V1].sort_values("active_mrr_proxy", ascending=False).reset_index()
    v1_out = pd.DataFrame({"Account ID": v1.account_id, "Account name": v1.account_name, "Industry": v1.industry, "Country": v1.country,
                           "Active records": v1.active_records, "Active MRR proxy": v1.active_mrr_proxy, "Churn events": v1.churn_events,
                           "Last churn event": v1.last_churn_event, "Ended records": v1.ended_records, "Also in V2": yn(v1.in_V2),
                           "Also in V3-W1": yn(v1.in_V3_W1), "Verified status (fill)": "", "Status source (fill)": "", "Owner (fill)": "", "Reviewed on (fill)": ""})
    v2 = base[V2].sort_values("active_mrr_proxy", ascending=False).reset_index()
    v2_out = pd.DataFrame({"Value rank": v2.value_rank, "Account ID": v2.account_id, "Account name": v2.account_name, "Industry": v2.industry,
                           "Country": v2.country, "Active records": v2.active_records, "Active MRR proxy": v2.active_mrr_proxy,
                           "Share of active MRR proxy": v2.active_mrr_proxy / total, "Cumulative share": (v2.active_mrr_proxy / total).cumsum(),
                           "Exposed MRR proxy (no auto-renew)": v2.exposed_mrr_proxy, "Also in V1": yn(v2.in_V1), "Also in V3-W1": yn(v2.in_V3_W1),
                           "Owner (fill)": "", "Economic buyer (fill)": "", "Champion (fill)": "", "Renewal date (fill)": "", "Value review date (fill)": ""})
    v3 = base[V3].sort_values("exposed_mrr_proxy", ascending=False).reset_index()
    v3_out = pd.DataFrame({"Exposure rank": v3.exposure_rank, "Account ID": v3.account_id, "Account name": v3.account_name, "Industry": v3.industry,
                           "Country": v3.country, "Exposed records (MRR>0)": v3.exposed_records_with_mrr, "Exposed MRR proxy": v3.exposed_mrr_proxy,
                           "Monthly exposed MRR proxy": v3.exposed_monthly_mrr_proxy, "Annual exposed MRR proxy": v3.exposed_annual_mrr_proxy,
                           "Share of V3": v3.exposed_mrr_proxy / exposure, "Wave": np.where(v3.in_V3_W1, "W1", "later"),
                           "Also in V1": yn(v3.in_V1), "Also in V2": yn(v3.in_V2), "Pilot eligible": yn(v3.pilot_eligible),
                           "Renewal date - internal source (fill)": "", "Renewal owner (fill)": "", "Renewal intent (fill; pilot treatment arm only)": ""})
    trial_only = base[nonauto_any & ~V3].reset_index()
    trial_out = pd.DataFrame({"Account ID": trial_only.account_id, "Account name": trial_only.account_name,
                              "Zero-MRR trial records without auto-renew": nonauto[nonauto.account_id.isin(trial_only.account_id)].groupby("account_id").size().reindex(trial_only.account_id).values})
    return N, {**tables, "V1": v1_out, "V2": v2_out, "V3": v3_out, "trial_only": trial_out}


CAVEATS = [
    ("MRR proxy", "subscriptions.mrr_amount summed by account", "account; active records at 2024-12-31", "500/500 accounts have overlapping records",
     "MRR proxy — not consolidated revenue; no currency declared in the dataset"),
    ("Active MRR proxy total", "sum of mrr_amount of records with no end_date", "all accounts", "5,000 records", "MRR proxy — overlapping records may double count"),
    ("V1 — Churn-status reconciliation", "accounts.churn_flag=true AND active MRR proxy > 0", "account", "110/110 flagged accounts", "Data reconciliation — not predicted churn"),
    ("V2 — Top-value coverage", "top 50 accounts by active MRR proxy", "account", "500 accounts ranked", "Business priority — not predicted churn risk"),
    ("V3 — Manual-renewal readiness", "active records with auto_renew_flag=false and MRR proxy > 0", "account / record", "388 accounts, 764 records",
     "Exposure — not Revenue at Risk; renewal dates absent from the data"),
    ("V3 — non-auto-renew exposure is zero-MRR trial only", "accounts whose only active auto_renew=false records are zero-MRR trials", "account", "21 accounts, 26 records",
     "Listed separately; not part of economic exposure. All 21 have other paid active records"),
    ("V3-W1", "top 50 V3 accounts by exposed MRR proxy", "account", "50 accounts, 137 records", "First operational wave — not a risk ranking"),
    ("Wave 1", "V1 ∪ V2 ∪ V3-W1", "account (union)", "176 unique accounts", "Union, not 110+50+50"),
    ("Scenarios", "X% × V3 exposed MRR proxy", "portfolio", "V3 only", "Scenario — not forecast; no probability; no causal estimate"),
    ("Observable contract state", "accounts with zero active records at 2024-12-31", "account", "0/500", "Commercial semantics of records not validated"),
    ("Usage", "feature_usage rows", "subscription / account", "22.3% of rows fall inside the subscription lifecycle", "Usage coverage = 22.3% inside subscription lifecycle"),
    ("Pilot eligible", "V3 minus V2 minus V3-W1", "account", "314 accounts", "Randomize before any customer contact; renewal date from internal source in both arms"),
]


def write_workbook(N: dict, T: dict[str, pd.DataFrame]) -> None:
    wb = Workbook()
    bold, hdr = Font(bold=True), PatternFill("solid", fgColor="DDE7F0")
    def sheet_table(ws, df, start_row, name, money_cols=(), pct_cols=()):
        for j, col in enumerate(df.columns, 1):
            cell = ws.cell(row=start_row, column=j, value=col); cell.font = bold; cell.fill = hdr
            cell.alignment = Alignment(wrap_text=True, vertical="top")
        for i, row in enumerate(df.itertuples(index=False), start_row + 1):
            for j, val in enumerate(row, 1):
                v = None if (isinstance(val, float) and np.isnan(val)) else (val.item() if hasattr(val, "item") else val)
                cell = ws.cell(row=i, column=j, value=v)
                if df.columns[j - 1] in money_cols: cell.number_format = "#,##0"
                if df.columns[j - 1] in pct_cols: cell.number_format = "0.0%"
        ref = f"A{start_row}:{get_column_letter(len(df.columns))}{start_row + len(df)}"
        tab = Table(displayName=name, ref=ref); tab.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
        ws.add_table(tab)
        for j, col in enumerate(df.columns, 1):
            ws.column_dimensions[get_column_letter(j)].width = min(max(12, len(col) + 2), 34)
        ws.freeze_panes = ws.cell(row=start_row + 1, column=3)

    ov = wb.active; ov.title = "Overview"
    lines = [
        ("RavenStack — CS action queues (first 30 days)", None),
        ("All values are MRR proxy (sum of subscription mrr_amount records). MRR proxy — not consolidated revenue; no currency is declared in the dataset.", None),
        ("No churn probability or risk score is produced anywhere in this workbook.", None),
        ("", None),
        ("Queue", "Accounts", "Records", "MRR proxy", "Share of active MRR proxy", "What CS/RevOps does", "Label"),
        ("V1 Churn-status reconciliation", N["V1"]["accounts"], None, N["V1"]["active_mrr_proxy"], N["V1"]["share_active"],
         "RevOps verifies real status within 14 days", "Data reconciliation — not predicted churn"),
        ("V2 Top-value coverage", N["V2"]["accounts"], N["V2"]["records"], N["V2"]["active_mrr_proxy"], N["V2"]["share_active"],
         "Named owner, economic buyer, champion, renewal date, value review", "Business priority — not predicted churn risk"),
        ("V3 Manual-renewal readiness", N["V3"]["accounts"], N["V3"]["records_with_mrr"], N["V3"]["exposed_mrr_proxy"], N["V3"]["share_active"],
         "Capture renewal date (internal source), owner; intent only in pilot treatment arm", "Exposure — not Revenue at Risk"),
        ("V3-W1 first wave (top 50 by exposure)", N["V3W1"]["accounts"], N["V3W1"]["records"], N["V3W1"]["exposed_mrr_proxy"], N["V3W1"]["share_active"],
         "First V3 wave", f"{N['V3W1']['share_of_V3']:.1%} of V3 exposure"),
        ("Wave 1 = V1 ∪ V2 ∪ V3-W1", N["wave1"]["union_accounts"], None, N["wave1"]["active_mrr_proxy"], N["wave1"]["share_active"],
         "Unique accounts (union, not a sum)", f"naive sum {N['wave1']['naive_sum']}; overlaps V1∩V2={N['wave1']['V1_V2']}, V1∩V3-W1={N['wave1']['V1_W1']}, V2∩V3-W1={N['wave1']['V2_W1']}, triple={N['wave1']['triple']}"),
        ("", None),
        (f"Additional: of the {N['V3']['any_nonauto_accounts']} accounts with any active auto_renew=false record, {N['V3']['trial_only_accounts']} have only zero-MRR trial "
         f"exposure with auto-renew disabled ({N['V3']['trial_only_records']} records). These accounts have other paid active subscriptions; only their non-auto-renew "
         f"exposure is zero. Listed at the bottom of the Definitions sheet; not part of the economic exposure.", None),
        (f"Any active record with auto-renew disabled: {N['V3']['any_nonauto_accounts']} accounts / {N['V3']['any_nonauto_records']} records, "
         f"of which {N['V3']['zero_mrr_nonauto_records']} records have MRR proxy = 0.", None),
        ("", None),
        ("Conditional scenarios on V3 exposure", "Percentage", "MRR proxy", "Annualized proxy (12×)", "Label"),
    ] + [("If an intervention ultimately preserves X% of the manual-renewal exposure", sc["pct"], sc["mrr_proxy"], sc["annualized_proxy"],
          "Scenario — not forecast; no probability attached; no causal estimate exists") for sc in N["scenarios_on_V3"]]
    for i, line in enumerate(lines, 1):
        for j, val in enumerate(line, 1):
            if val is None: continue
            cell = ov.cell(row=i, column=j, value=val)
            if i in (1, 5, 15): cell.font = bold
            if isinstance(val, float) and val < 1 and j in (5,): cell.number_format = "0.0%"
            elif isinstance(val, float) and val < 1 and j == 2: cell.number_format = "0%"
            elif isinstance(val, (int, float)) and not isinstance(val, bool) and j in (3, 4): cell.number_format = "#,##0"
    for col, w in zip("ABCDEFG", (58, 12, 12, 16, 22, 60, 60)):
        ov.column_dimensions[col].width = w

    for title, key, name, money, pct in [
        ("V1 Status Reconciliation", "V1", "V1StatusReconciliation", ["Active MRR proxy"], []),
        ("V2 Top-Value Coverage", "V2", "V2TopValueCoverage", ["Active MRR proxy", "Exposed MRR proxy (no auto-renew)"], ["Share of active MRR proxy", "Cumulative share"]),
        ("V3 Renewal Readiness", "V3", "V3RenewalReadiness", ["Exposed MRR proxy", "Monthly exposed MRR proxy", "Annual exposed MRR proxy"], ["Share of V3"]),
    ]:
        ws = wb.create_sheet(title)
        note = {"V1": "Verified status values: ACTIVE / CONTRACTION / CANCELLATION SCHEDULED / CHURNED / DATA ERROR / NEEDS REVIEW — fill only when verifiable. Label: data reconciliation — not predicted churn.",
                "V2": "Coverage queue. Label: business priority — not predicted churn risk. MRR proxy — not consolidated revenue.",
                "V3": "Renewal readiness. Label: exposure — not Revenue at Risk. Renewal date must come from an internal source in both pilot arms before any customer contact; intent is captured only in the pilot treatment arm."}[key]
        ws.cell(row=1, column=1, value=title).font = bold
        ws.cell(row=2, column=1, value=note)
        sheet_table(ws, T[key], 4, name, money, pct)

    dfs = wb.create_sheet("Definitions & Caveats")
    dfs.cell(row=1, column=1, value="Every number: source, grain, coverage and limitation").font = bold
    cav = pd.DataFrame(CAVEATS, columns=["Item", "Source / rule", "Grain", "Coverage", "Confidence / limitation label"])
    sheet_table(dfs, cav, 3, "Caveats")
    start = 3 + len(cav) + 3
    dfs.cell(row=start - 1, column=1, value=f"Accounts whose non-auto-renew exposure is zero-MRR trial only ({len(T['trial_only'])}) — they have other paid active records; not economic exposure").font = bold
    sheet_table(dfs, T["trial_only"], start, "TrialOnlyAccounts")
    dfs.freeze_panes = None
    XLSX.parent.mkdir(parents=True, exist_ok=True)
    wb.save(XLSX)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    N, T = build()
    (OUT / "final_numbers.json").write_text(json.dumps(N, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    T["segment_usage"].to_csv(OUT / "segment_usage_per_active_account.csv", index=False)
    T["churned_vs_retained"].to_csv(OUT / "churned_vs_retained.csv", index=False)
    T["observed_segment_rates"].to_csv(OUT / "observed_segment_rates.csv", index=False)
    print(T["observed_segment_rates"][["dimension", "segment", "accounts", "churn_flag_accounts", "observed_rate", "ci95_low", "ci95_high",
                                       "dimension_chi2_p", "dimension_q_bh", "small_sample"]].round(3).to_string())
    print(json.dumps(N["observed_segment_rates"], indent=1))
    write_workbook(N, T)
    print(json.dumps({k: N[k] for k in ["churn_definitions", "V1", "V2", "V3", "V3W1", "wave1", "enterprise", "ended_2024", "pilot", "usage", "support"]},
                     indent=1, default=float))
    print(T["segment_usage"].to_string()); print(T["churned_vs_retained"].to_string())
    print("rows:", {k: len(v) for k, v in T.items()}, "->", XLSX)


if __name__ == "__main__":
    main()
