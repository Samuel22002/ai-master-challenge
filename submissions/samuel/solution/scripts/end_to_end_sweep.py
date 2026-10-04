"""ANALYSIS-14 — End-to-end five-table sweep.

Profiles every column of the five RavenStack tables, builds a monthly KPI layer,
a one-row-per-account master table joining all five tables, segment outcome rates
with confidence intervals and FDR, per-feature and per-priority views, revenue
weighting, and an end-to-end predictive test (cross-validated, permutation null).

Run: python solution/scripts/end_to_end_sweep.py
"""
from __future__ import annotations

import json
import math
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import RepeatedStratifiedKFold, StratifiedKFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from statsmodels.genmod.families import Poisson
from statsmodels.genmod.generalized_linear_model import GLM
from statsmodels.stats.multitest import multipletests

warnings.filterwarnings("ignore")
from _paths import OUTPUTS, PKG, RAW_DIR, ROOT  # noqa: E402,F401  (package paths)
RAW = RAW_DIR
OUT = OUTPUTS / "end_to_end_sweep"
OBS_END = pd.Timestamp("2024-12-31")
SEED = 20261004


def load() -> dict[str, pd.DataFrame]:
    return {
        "accounts": pd.read_csv(RAW / "ravenstack_accounts.csv", parse_dates=["signup_date"]),
        "subscriptions": pd.read_csv(RAW / "ravenstack_subscriptions.csv", parse_dates=["start_date", "end_date"]),
        "feature_usage": pd.read_csv(RAW / "ravenstack_feature_usage.csv", parse_dates=["usage_date"]),
        "support_tickets": pd.read_csv(RAW / "ravenstack_support_tickets.csv", parse_dates=["submitted_at", "closed_at"]),
        "churn_events": pd.read_csv(RAW / "ravenstack_churn_events.csv", parse_dates=["churn_date"]),
    }


def wilson(k: float, n: float) -> tuple[float, float]:
    if n == 0:
        return np.nan, np.nan
    z, p = 1.96, k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def poisson_ci(k: float, exposure: float, per: float = 1.0) -> tuple[float, float]:
    lo = stats.chi2.ppf(0.025, 2 * k) / 2 if k else 0.0
    hi = stats.chi2.ppf(0.975, 2 * k + 2) / 2
    return per * lo / exposure, per * hi / exposure


# ------------------------------------------------------------------ 1. column profile
def column_profile(d: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for table, df in d.items():
        for col in df.columns:
            x = df[col]
            row = {"table": table, "column": col, "dtype": str(x.dtype), "rows": len(x), "nulls": int(x.isna().sum()),
                   "null_pct": x.isna().mean(), "distinct": int(x.nunique(dropna=True))}
            if pd.api.types.is_bool_dtype(x):
                row["summary"] = f"true={x.mean():.3f}"
            elif pd.api.types.is_numeric_dtype(x):
                q = x.quantile([0, .25, .5, .75, 1])
                row["summary"] = f"mean={x.mean():.2f} sd={x.std():.2f} min={q[0]:.2f} p25={q[.25]:.2f} p50={q[.5]:.2f} p75={q[.75]:.2f} max={q[1]:.2f}"
            elif pd.api.types.is_datetime64_any_dtype(x):
                row["summary"] = f"min={x.min().date()} max={x.max().date()}"
            else:
                vc = x.value_counts(dropna=False)
                row["summary"] = "; ".join(f"{k}={v}" for k, v in vc.head(8).items()) if len(vc) <= 50 else f"high cardinality; top={vc.index[0]} ({vc.iloc[0]})"
            rows.append(row)
    return pd.DataFrame(rows)


def join_integrity(d: dict[str, pd.DataFrame]) -> pd.DataFrame:
    a, s, u, t, c = (d[k] for k in ["accounts", "subscriptions", "feature_usage", "support_tickets", "churn_events"])
    us = u.merge(s[["subscription_id", "account_id"]], on="subscription_id", how="left")
    rows = [
        ("subscriptions -> accounts", len(s), int(s.account_id.isin(a.account_id).sum()), s.account_id.nunique()),
        ("feature_usage -> subscriptions", len(u), int(u.subscription_id.isin(s.subscription_id).sum()), u.subscription_id.nunique()),
        ("feature_usage -> subscriptions -> accounts", len(us), int(us.account_id.notna().sum()), us.account_id.nunique()),
        ("support_tickets -> accounts", len(t), int(t.account_id.isin(a.account_id).sum()), t.account_id.nunique()),
        ("churn_events -> accounts", len(c), int(c.account_id.isin(a.account_id).sum()), c.account_id.nunique()),
    ]
    out = pd.DataFrame(rows, columns=["join", "child_rows", "child_rows_matched", "distinct_parents_reached"])
    out["row_multiplication"] = [len(s.merge(a, on="account_id")) - len(s), len(u.merge(s, on="subscription_id")) - len(u),
                                 len(us) - len(u), len(t.merge(a, on="account_id")) - len(t), len(c.merge(a, on="account_id")) - len(c)]
    return out


# ------------------------------------------------------------------ 2. monthly KPI layer
def monthly_kpis(d: dict[str, pd.DataFrame]) -> pd.DataFrame:
    a, s, u, t, c = (d[k] for k in ["accounts", "subscriptions", "feature_usage", "support_tickets", "churn_events"])
    first_start = s.groupby("account_id").start_date.min()
    rows = []
    for p in pd.period_range("2023-01", "2024-12", freq="M"):
        lo, hi = p.start_time, p.end_time.normalize()
        active = s[(s.start_date <= hi) & (s.end_date.isna() | (s.end_date > hi))]
        accounts_signed = int((a.signup_date <= hi).sum())
        accounts_active = int(active.account_id.nunique())
        um = u[(u.usage_date >= lo) & (u.usage_date <= hi)]
        tm = t[(t.submitted_at >= lo) & (t.submitted_at <= hi)]
        cm = c[(c.churn_date >= lo) & (c.churn_date <= hi)]
        ends = s[(s.end_date >= lo) & (s.end_date <= hi)]
        rows.append({
            "month": str(p), "new_signups": int(a.signup_date.between(lo, hi).sum()), "accounts_signed_cum": accounts_signed,
            "accounts_with_active_sub_eom": accounts_active, "new_subscriptions": int(s.start_date.between(lo, hi).sum()),
            "ended_subscriptions": len(ends), "active_subscriptions_eom": len(active),
            "active_mrr_proxy_eom": int(active.mrr_amount.sum()), "ended_mrr_proxy": int(ends.mrr_amount.sum()),
            "usage_rows": len(um), "usage_count": int(um.usage_count.sum()), "usage_errors": int(um.error_count.sum()),
            "usage_per_signed_account": um.usage_count.sum() / max(accounts_signed, 1),
            "usage_per_active_account": um.usage_count.sum() / max(accounts_active, 1),
            "usage_per_active_subscription": um.usage_count.sum() / max(len(active), 1),
            "error_rate": um.error_count.sum() / max(um.usage_count.sum(), 1),
            "tickets": len(tm), "tickets_per_100_accounts": 100 * len(tm) / max(accounts_signed, 1),
            "escalations": int(tm.escalation_flag.sum()), "csat_mean": tm.satisfaction_score.mean(),
            "csat_response_rate": tm.satisfaction_score.notna().mean() if len(tm) else np.nan,
            "churn_events": len(cm), "churn_events_per_100_accounts": 100 * len(cm) / max(accounts_signed, 1),
            "reactivation_events": int(cm.is_reactivation.sum()), "refund_usd": float(cm.refund_amount_usd.sum()),
            "ended_subs_per_100_active": 100 * len(ends) / max(len(active) + len(ends), 1),
        })
    return pd.DataFrame(rows)


def quarterly_claims(monthly: pd.DataFrame) -> pd.DataFrame:
    m = monthly.copy()
    m["quarter"] = pd.PeriodIndex(m.month, freq="M").asfreq("Q").astype(str)
    g = m.groupby("quarter")
    q = pd.DataFrame({
        "accounts_signed_eoq": g.accounts_signed_cum.last(), "accounts_active_eoq": g.accounts_with_active_sub_eom.last(),
        "active_subscriptions_eoq": g.active_subscriptions_eom.last(), "usage_total": g.usage_count.sum(),
        "csat_mean_ticket_weighted": g.apply(lambda x: np.average(x.csat_mean.fillna(0), weights=x.tickets * x.csat_response_rate.fillna(0)), include_groups=False),
        "tickets": g.tickets.sum(), "churn_events": g.churn_events.sum(), "ended_subscriptions": g.ended_subscriptions.sum(),
    })
    q["usage_per_account"] = q.usage_total / q.accounts_signed_eoq
    q["usage_per_active_account"] = q.usage_total / q.accounts_active_eoq
    q["usage_per_active_subscription"] = q.usage_total / q.active_subscriptions_eoq
    q["churn_events_per_100_accounts"] = 100 * q.churn_events / q.accounts_signed_eoq
    q["usage_total_index_2023Q1"] = 100 * q.usage_total / q.usage_total.iloc[0]
    q["usage_per_account_index_2023Q1"] = 100 * q.usage_per_account / q.usage_per_account.iloc[0]
    return q.reset_index()


# ------------------------------------------------------------------ 3. account master (all five tables)
def account_master(d: dict[str, pd.DataFrame]) -> pd.DataFrame:
    a, s, u, t, c = (d[k] for k in ["accounts", "subscriptions", "feature_usage", "support_tickets", "churn_events"])
    m = a.set_index("account_id").copy()
    m["tenure_years"] = ((OBS_END - m.signup_date).dt.days + 1) / 365.25
    m["signup_half"] = m.signup_date.dt.year.astype(str) + "H" + np.where(m.signup_date.dt.month <= 6, "1", "2")
    m["seats_band"] = pd.cut(m.seats, [0, 5, 15, 30, 1000], labels=["1-5", "6-15", "16-30", "31+"]).astype(str)
    active = s[s.end_date.isna()]
    m = m.join(s.groupby("account_id").agg(
        subs_total=("subscription_id", "size"), subs_ended=("end_date", lambda x: x.notna().sum()),
        sub_mrr_median=("mrr_amount", "median"), sub_trial_share=("is_trial", "mean"), sub_upgrade_share=("upgrade_flag", "mean"),
        sub_downgrade_share=("downgrade_flag", "mean"), sub_annual_share=("billing_frequency", lambda x: (x == "annual").mean()),
        sub_autorenew_share=("auto_renew_flag", "mean"), sub_seats_median=("seats", "median"),
        sub_enterprise_share=("plan_tier", lambda x: (x == "Enterprise").mean())))
    m = m.join(active.groupby("account_id").agg(active_subs_eop=("subscription_id", "size"), active_mrr_proxy_eop=("mrr_amount", "sum"),
                                                active_non_autorenew_subs=("auto_renew_flag", lambda x: (~x).sum())))
    us = u.merge(s[["subscription_id", "account_id"]], on="subscription_id")
    m = m.join(us.groupby("account_id").agg(
        usage_rows=("usage_id", "size"), usage_count=("usage_count", "sum"), usage_duration_h=("usage_duration_secs", lambda x: x.sum() / 3600),
        usage_errors=("error_count", "sum"), usage_features=("feature_name", "nunique"), usage_beta_share=("is_beta_feature", "mean"),
        usage_active_days=("usage_date", "nunique")))
    m["usage_error_rate"] = m.usage_errors / m.usage_count.replace(0, np.nan)
    m["usage_per_year"] = m.usage_count / m.tenure_years
    m = m.join(t.groupby("account_id").agg(
        tickets=("ticket_id", "size"), ticket_resolution_h=("resolution_time_hours", "mean"),
        ticket_first_response_min=("first_response_time_minutes", "mean"), ticket_escalations=("escalation_flag", "sum"),
        ticket_urgent_high_share=("priority", lambda x: x.isin(["urgent", "high"]).mean()),
        csat_mean=("satisfaction_score", "mean"), csat_min=("satisfaction_score", "min"),
        csat_no_response_share=("satisfaction_score", lambda x: x.isna().mean())))
    m[["tickets", "ticket_escalations"]] = m[["tickets", "ticket_escalations"]].fillna(0)
    m["tickets_per_year"] = m.tickets / m.tenure_years
    m = m.join(c.groupby("account_id").agg(
        churn_events=("churn_event_id", "size"), reactivation_events=("is_reactivation", "sum"), refund_usd=("refund_amount_usd", "sum"),
        first_churn_event=("churn_date", "min")))
    m[["churn_events", "reactivation_events", "refund_usd"]] = m[["churn_events", "reactivation_events", "refund_usd"]].fillna(0)
    m["has_churn_event"] = m.churn_events > 0
    m["churn_events_per_year"] = m.churn_events / m.tenure_years
    m["any_sub_ended"] = m.subs_ended > 0
    return m


# ------------------------------------------------------------------ 4. segment outcome rates
def segment_outcomes(m: pd.DataFrame, s: pd.DataFrame, accounts: pd.DataFrame) -> pd.DataFrame:
    rows = []
    segs = ["industry", "country", "referral_source", "plan_tier", "is_trial", "seats_band", "signup_half"]
    # account-level binary outcomes
    for outcome in ["churn_flag", "has_churn_event", "any_sub_ended"]:
        y = m[outcome].astype(bool)
        for seg in segs:
            ct = pd.crosstab(m[seg].astype(str), y)
            p = stats.chi2_contingency(ct)[1]
            for lvl, r in ct.iterrows():
                n, k = int(r.sum()), int(r.get(True, 0))
                lo, hi = wilson(k, n)
                rows.append({"outcome": outcome, "grain": "account", "segment": seg, "level": lvl, "n": n, "events": k,
                             "rate": k / n, "ci95_low": lo, "ci95_high": hi, "overall_rate": y.mean(), "test_p_value": p, "test": "chi2"})
    # account churn events per account-year (exposure-adjusted)
    for seg in segs:
        g = m.groupby(m[seg].astype(str)).agg(ev=("churn_events", "sum"), ex=("tenure_years", "sum"), n=("churn_events", "size"))
        x = pd.get_dummies(m[seg].astype(str), drop_first=True, dtype=float)
        x.insert(0, "const", 1.0)
        full = GLM(m.churn_events, x, family=Poisson(), offset=np.log(m.tenure_years)).fit()
        null = GLM(m.churn_events, x[["const"]], family=Poisson(), offset=np.log(m.tenure_years)).fit()
        p = stats.chi2.sf(2 * (full.llf - null.llf), x.shape[1] - 1)
        for lvl, r in g.iterrows():
            lo, hi = poisson_ci(r.ev, r.ex)
            rows.append({"outcome": "churn_events_per_account_year", "grain": "account", "segment": seg, "level": lvl, "n": int(r.n),
                         "events": int(r.ev), "rate": r.ev / r.ex, "ci95_low": lo, "ci95_high": hi,
                         "overall_rate": m.churn_events.sum() / m.tenure_years.sum(), "test_p_value": p, "test": "Poisson LR"})
    # subscription ends per 100 subscription-months, by subscription and account attributes
    ss = s.merge(accounts[["account_id", "industry", "country", "referral_source"]], on="account_id")
    ss["exposure_m"] = ((ss.end_date.fillna(OBS_END) - ss.start_date).dt.days + 1) / 30.4375
    ss["ended"] = ss.end_date.notna().astype(int)
    ss["seats_band"] = pd.cut(ss.seats, [0, 10, 25, 50, 1000], labels=["1-10", "11-25", "26-50", "51+"]).astype(str)
    ss["start_half"] = ss.start_date.dt.year.astype(str) + "H" + np.where(ss.start_date.dt.month <= 6, "1", "2")
    for seg in ["plan_tier", "billing_frequency", "is_trial", "auto_renew_flag", "upgrade_flag", "downgrade_flag", "seats_band",
                "industry", "country", "referral_source", "start_half"]:
        g = ss.groupby(ss[seg].astype(str)).agg(ev=("ended", "sum"), ex=("exposure_m", "sum"), n=("ended", "size"))
        x = pd.get_dummies(ss[seg].astype(str), drop_first=True, dtype=float)
        x.insert(0, "const", 1.0)
        full = GLM(ss.ended, x, family=Poisson(), offset=np.log(ss.exposure_m)).fit()
        null = GLM(ss.ended, x[["const"]], family=Poisson(), offset=np.log(ss.exposure_m)).fit()
        p = stats.chi2.sf(2 * (full.llf - null.llf), x.shape[1] - 1)
        for lvl, r in g.iterrows():
            lo, hi = poisson_ci(r.ev, r.ex, 100)
            rows.append({"outcome": "subscription_ends_per_100_sub_months", "grain": "subscription", "segment": seg, "level": lvl,
                         "n": int(r.n), "events": int(r.ev), "rate": 100 * r.ev / r.ex, "ci95_low": lo, "ci95_high": hi,
                         "overall_rate": 100 * ss.ended.sum() / ss.exposure_m.sum(), "test_p_value": p, "test": "Poisson LR"})
    out = pd.DataFrame(rows)
    tests = out.drop_duplicates(["outcome", "segment"])[["outcome", "segment", "test_p_value"]].copy()
    tests["q_value_bh"] = multipletests(tests.test_p_value, method="fdr_bh")[1]
    return out.merge(tests[["outcome", "segment", "q_value_bh"]], on=["outcome", "segment"])


# ------------------------------------------------------------------ 5. table-specific deep views
def feature_view(d: dict[str, pd.DataFrame]) -> pd.DataFrame:
    s, u = d["subscriptions"], d["feature_usage"]
    us = u.merge(s[["subscription_id", "end_date", "plan_tier"]], on="subscription_id")
    ended_subs = set(s[s.end_date.notna()].subscription_id)
    n_end, n_act = len(ended_subs), len(s) - len(ended_subs)
    rows = []
    for f, g in us.groupby("feature_name"):
        subs = set(g.subscription_id)
        k_end, k_act = len(subs & ended_subs), len(subs - ended_subs)
        p = stats.fisher_exact([[k_end, n_end - k_end], [k_act, n_act - k_act]])[1]
        rows.append({"feature": f, "usage_rows": len(g), "usage_count": int(g.usage_count.sum()), "subscriptions_using": len(subs),
                     "errors": int(g.error_count.sum()), "error_rate": g.error_count.sum() / max(g.usage_count.sum(), 1),
                     "beta_share": g.is_beta_feature.mean(), "avg_duration_min": g.usage_duration_secs.mean() / 60,
                     "share_of_ended_subs_using": k_end / n_end, "share_of_active_subs_using": k_act / n_act,
                     "adoption_diff_pp": 100 * (k_end / n_end - k_act / n_act), "fisher_p_ended_vs_active": p,
                     "enterprise_share_of_rows": (g.plan_tier == "Enterprise").mean()})
    out = pd.DataFrame(rows)
    out["q_value_bh"] = multipletests(out.fisher_p_ended_vs_active, method="fdr_bh")[1]
    out["error_rate_vs_mean_chi2_p"] = [stats.chisquare([r.errors, r.usage_count - r.errors],
                                                        [r.usage_count * out.errors.sum() / out.usage_count.sum(),
                                                         r.usage_count * (1 - out.errors.sum() / out.usage_count.sum())])[1] for r in out.itertuples()]
    return out.sort_values("usage_count", ascending=False)


def support_view(d: dict[str, pd.DataFrame]) -> pd.DataFrame:
    t = d["support_tickets"]
    rows = []
    for key, g in [("ALL", t)] + [(f"priority={k}", g) for k, g in t.groupby("priority")] + [(f"escalated={k}", g) for k, g in t.groupby("escalation_flag")]:
        rows.append({"group": key, "tickets": len(g), "resolution_h_mean": g.resolution_time_hours.mean(), "resolution_h_p90": g.resolution_time_hours.quantile(.9),
                     "first_response_min_mean": g.first_response_time_minutes.mean(), "escalation_rate": g.escalation_flag.mean(),
                     "csat_response_rate": g.satisfaction_score.notna().mean(), "csat_mean": g.satisfaction_score.mean(),
                     "csat_3_share": (g.satisfaction_score == 3).sum() / max(g.satisfaction_score.notna().sum(), 1),
                     "csat_5_share": (g.satisfaction_score == 5).sum() / max(g.satisfaction_score.notna().sum(), 1)})
    return pd.DataFrame(rows)


def event_view(d: dict[str, pd.DataFrame], m: pd.DataFrame) -> dict[str, pd.DataFrame]:
    c, a, s = d["churn_events"], d["accounts"], d["subscriptions"]
    ce = c.merge(a[["account_id", "signup_date", "churn_flag", "plan_tier", "industry"]], on="account_id")
    first_sub = s.groupby("account_id").start_date.min()
    ce["before_first_subscription"] = ce.churn_date < ce.account_id.map(first_sub)
    ce["active_subs_at_event"] = [int(((s.account_id == r.account_id) & (s.start_date <= r.churn_date) &
                                       (s.end_date.isna() | (s.end_date >= r.churn_date))).sum()) for r in ce.itertuples()]
    ce = ce.sort_values(["account_id", "churn_date"])
    ce["event_seq"] = ce.groupby("account_id").cumcount() + 1
    reason = ce.groupby("reason_code").agg(events=("churn_event_id", "size"), accounts=("account_id", "nunique"),
                                           refund_share=("refund_amount_usd", lambda x: (x > 0).mean()), refund_mean=("refund_amount_usd", "mean"),
                                           reactivation_share=("is_reactivation", "mean"), preceding_upgrade_share=("preceding_upgrade_flag", "mean"),
                                           preceding_downgrade_share=("preceding_downgrade_flag", "mean"),
                                           flagged_account_share=("churn_flag", "mean"), before_first_sub_share=("before_first_subscription", "mean"),
                                           active_subs_at_event_median=("active_subs_at_event", "median"))
    reason["share"] = reason.events / reason.events.sum()
    xtab = pd.crosstab(ce.reason_code, ce.feedback_text.fillna("NO_FEEDBACK"))
    seq = ce.groupby("event_seq").agg(events=("churn_event_id", "size"), reactivation_share=("is_reactivation", "mean")).reset_index()
    timing = pd.DataFrame([{
        "events": len(ce), "events_before_first_subscription": int(ce.before_first_subscription.sum()),
        "events_with_zero_active_subs": int((ce.active_subs_at_event == 0).sum()),
        "events_with_2plus_active_subs": int((ce.active_subs_at_event >= 2).sum()),
        "median_active_subs_at_event": ce.active_subs_at_event.median(),
        "first_event_marked_reactivation": int(((ce.event_seq == 1) & ce.is_reactivation).sum()),
        "accounts_flagged_without_event": int((m.churn_flag & ~m.has_churn_event).sum()),
        "accounts_with_event_not_flagged": int((~m.churn_flag & m.has_churn_event).sum()),
    }])
    return {"event_reason_profile.csv": reason.reset_index(), "event_reason_x_feedback.csv": xtab.reset_index(),
            "event_sequence_profile.csv": seq, "event_timing_checks.csv": timing}


def revenue_view(d: dict[str, pd.DataFrame]) -> pd.DataFrame:
    s, a = d["subscriptions"], d["accounts"]
    ss = s.merge(a[["account_id", "industry", "referral_source"]], on="account_id")
    rows = []
    for seg in ["plan_tier", "billing_frequency", "industry", "referral_source"]:
        for lvl, g in ss.groupby(seg):
            act, end = g[g.end_date.isna()], g[g.end_date.notna()]
            rows.append({"segment": seg, "level": lvl, "records": len(g), "ended_records": len(end),
                         "ended_mrr_proxy": int(end.mrr_amount.sum()), "active_mrr_proxy": int(act.mrr_amount.sum()),
                         "ended_mrr_share_of_segment_mrr": end.mrr_amount.sum() / max(g.mrr_amount.sum(), 1),
                         "ended_record_share": len(end) / len(g), "mean_mrr_ended": end.mrr_amount.mean(), "mean_mrr_active": act.mrr_amount.mean(),
                         "active_non_autorenew_mrr": int(act[~act.auto_renew_flag].mrr_amount.sum())})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ 6. end-to-end predictive test
def predictive_test(m: pd.DataFrame, d: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    cat = ["industry", "country", "referral_source", "plan_tier", "signup_half"]
    num = ["seats", "tenure_years", "subs_total", "sub_mrr_median", "sub_trial_share", "sub_upgrade_share", "sub_downgrade_share",
           "sub_annual_share", "sub_autorenew_share", "sub_seats_median", "sub_enterprise_share", "usage_rows", "usage_count",
           "usage_duration_h", "usage_errors", "usage_features", "usage_beta_share", "usage_active_days", "usage_error_rate",
           "usage_per_year", "tickets", "ticket_resolution_h", "ticket_first_response_min", "ticket_escalations",
           "ticket_urgent_high_share", "csat_mean", "csat_min", "csat_no_response_share", "tickets_per_year"]
    bools = ["is_trial"]
    X = m[cat + num + bools].copy()
    X[bools] = X[bools].astype(float)
    pre = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore"), cat),
                             ("num", make_pipeline(SimpleImputer(strategy="median"), StandardScaler()), num + bools)])
    s = d["subscriptions"].merge(m[["industry", "country", "referral_source", "seats", "tickets", "csat_mean", "ticket_escalations"]]
                                 .rename(columns={"seats": "account_seats"}), left_on="account_id", right_index=True)
    ug = d["feature_usage"].groupby("subscription_id").agg(sub_usage_rows=("usage_id", "size"), sub_usage_count=("usage_count", "sum"),
                                                           sub_errors=("error_count", "sum"), sub_features=("feature_name", "nunique"))
    s = s.join(ug, on="subscription_id")
    s["start_month_index"] = (s.start_date.dt.year - 2023) * 12 + s.start_date.dt.month
    scat = ["plan_tier", "billing_frequency", "industry", "country", "referral_source"]
    snum = ["seats", "mrr_amount", "account_seats", "tickets", "csat_mean", "ticket_escalations", "sub_usage_rows", "sub_usage_count",
            "sub_errors", "sub_features", "start_month_index"]
    sbool = ["is_trial", "upgrade_flag", "downgrade_flag", "auto_renew_flag"]
    SX = s[scat + snum + sbool].copy()
    SX[sbool] = SX[sbool].astype(float)
    spre = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore"), scat),
                              ("num", make_pipeline(SimpleImputer(strategy="median"), StandardScaler()), snum + sbool)])
    tasks = [("account", "churn_flag", X, m.churn_flag.astype(int).values, pre),
             ("account", "has_churn_event", X, m.has_churn_event.astype(int).values, pre),
             ("subscription", "subscription_end", SX, s.end_date.notna().astype(int).values, spre)]
    rows, perm_rows = [], []
    rng = np.random.default_rng(SEED)
    for grain, outcome, XX, y, prep in tasks:
        models = {"logistic_l2": make_pipeline(prep, LogisticRegression(C=0.5, max_iter=2000)),
                  "decision_tree_depth4": make_pipeline(prep, DecisionTreeClassifier(max_depth=4, min_samples_leaf=20, random_state=SEED)),
                  "gradient_boosting": make_pipeline(prep, HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=200, random_state=SEED))}
        cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=3, random_state=SEED)
        for name, model in models.items():
            aucs, aps = [], []
            for tr, te in cv.split(XX, y):
                model.fit(XX.iloc[tr], y[tr])
                pr = model.predict_proba(XX.iloc[te])[:, 1]
                aucs.append(roc_auc_score(y[te], pr))
                aps.append(average_precision_score(y[te], pr))
            # top-decile lift and the out-of-fold AUC compared against the permutation null (same CV scheme)
            single_cv = StratifiedKFold(5, shuffle=True, random_state=SEED)
            pred = cross_val_predict(model, XX, y, cv=single_cv, method="predict_proba")[:, 1]
            top = pred >= np.quantile(pred, 0.9)
            rows.append({"grain": grain, "outcome": outcome, "model": name, "n": len(y), "prevalence": y.mean(),
                         "cv_roc_auc_mean": np.mean(aucs), "cv_roc_auc_sd": np.std(aucs), "cv_pr_auc_mean": np.mean(aps),
                         "pr_auc_baseline_prevalence": y.mean(), "top_decile_rate": y[top].mean(), "top_decile_lift": y[top].mean() / y.mean()})
            obs = roc_auc_score(y, pred)
            null = []
            for _ in range(100):
                yp = rng.permutation(y)
                pr = cross_val_predict(model, XX, yp, cv=single_cv, method="predict_proba")[:, 1]
                null.append(roc_auc_score(yp, pr))
            perm_rows.append({"grain": grain, "outcome": outcome, "model": name, "observed_oof_auc": obs, "null_auc_mean": np.mean(null),
                              "null_auc_p97_5": np.percentile(null, 97.5), "permutation_p": (1 + sum(np.array(null) >= obs)) / 101})
    return pd.DataFrame(rows), pd.DataFrame(perm_rows)


def univariate_account(m: pd.DataFrame) -> pd.DataFrame:
    num = ["seats", "tenure_years", "subs_total", "sub_mrr_median", "sub_trial_share", "sub_autorenew_share", "usage_count",
           "usage_per_year", "usage_errors", "usage_error_rate", "usage_features", "usage_active_days", "tickets", "tickets_per_year",
           "ticket_resolution_h", "ticket_first_response_min", "ticket_escalations", "csat_mean", "csat_no_response_share", "active_mrr_proxy_eop"]
    rows = []
    for outcome in ["churn_flag", "has_churn_event"]:
        y = m[outcome].astype(bool)
        for v in num:
            x1, x0 = m.loc[y, v].dropna(), m.loc[~y, v].dropna()
            pooled = math.sqrt((x1.var() + x0.var()) / 2)
            rows.append({"outcome": outcome, "variable": v, "mean_outcome": x1.mean(), "mean_other": x0.mean(),
                         "median_outcome": x1.median(), "median_other": x0.median(), "smd": (x1.mean() - x0.mean()) / pooled if pooled else np.nan,
                         "mwu_p": stats.mannwhitneyu(x1, x0).pvalue, "n_outcome": len(x1), "n_other": len(x0)})
    out = pd.DataFrame(rows)
    out["q_value_bh"] = multipletests(out.mwu_p, method="fdr_bh")[1]
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    d = load()
    m = account_master(d)
    monthly = monthly_kpis(d)
    outputs = {
        "column_profile.csv": column_profile(d), "join_integrity.csv": join_integrity(d),
        "monthly_kpis.csv": monthly, "quarterly_claims.csv": quarterly_claims(monthly),
        "account_master.csv": m.reset_index(), "segment_outcomes.csv": segment_outcomes(m, d["subscriptions"], d["accounts"]),
        "univariate_account.csv": univariate_account(m), "feature_view.csv": feature_view(d), "support_view.csv": support_view(d),
        "revenue_view.csv": revenue_view(d),
    }
    outputs.update(event_view(d, m))
    pred, perm = predictive_test(m, d)
    outputs["predictive_test.csv"] = pred
    outputs["predictive_permutation_null.csv"] = perm
    for name, df in outputs.items():
        df.to_csv(OUT / name, index=False)
    seg = outputs["segment_outcomes.csv"].drop_duplicates(["outcome", "segment"])
    meta = {"analysis_id": "ANALYSIS-14", "seed": SEED, "outputs": sorted(outputs),
            "segment_tests": int(len(seg)), "segment_tests_p_lt_05": int((seg.test_p_value < .05).sum()),
            "segment_tests_q_lt_10": int((seg.q_value_bh < .10).sum()),
            "univariate_tests_q_lt_10": int((outputs["univariate_account.csv"].q_value_bh < .10).sum()),
            "feature_tests_q_lt_10": int((outputs["feature_view.csv"].q_value_bh < .10).sum())}
    (OUT / "analysis_metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps(meta, indent=2))
    print(pred.round(3).to_string())
    print(perm.round(3).to_string())


if __name__ == "__main__":
    main()
