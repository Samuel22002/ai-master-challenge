"""INDEPENDENT AUDIT-01 — second-opinion forensic audit of the churn diagnosis.

Rebuilds every audited claim from the raw CSVs, recovers the synthetic generator's
date mechanics and tests prior findings against a calibrated null (the generator
with zero covariate effect). Prior scripts and outputs are read only for
reproduction checks; nothing upstream is modified.

Run: python solution/scripts/independent_audit.py [--sims 1000]
"""
from __future__ import annotations

import argparse
import json
import math
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.genmod.families import Poisson
from statsmodels.genmod.generalized_linear_model import GLM
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.power import TTestIndPower

warnings.filterwarnings("ignore")
from _paths import OUTPUTS, PKG, RAW_DIR, ROOT  # noqa: E402,F401  (package paths)
RAW = RAW_DIR
OUT = OUTPUTS / "independent_audit"
OBS_END = pd.Timestamp("2024-12-31")
OBS_D = np.datetime64("2024-12-31")
SEED = 20261004


def load() -> dict[str, pd.DataFrame]:
    return {
        "accounts": pd.read_csv(RAW / "ravenstack_accounts.csv", parse_dates=["signup_date"]),
        "subscriptions": pd.read_csv(RAW / "ravenstack_subscriptions.csv", parse_dates=["start_date", "end_date"]),
        "usage": pd.read_csv(RAW / "ravenstack_feature_usage.csv", parse_dates=["usage_date"]),
        "tickets": pd.read_csv(RAW / "ravenstack_support_tickets.csv", parse_dates=["submitted_at", "closed_at"]),
        "events": pd.read_csv(RAW / "ravenstack_churn_events.csv", parse_dates=["churn_date"]),
    }


def smd(x1: pd.Series, x0: pd.Series) -> float:
    pooled = math.sqrt((x1.var() + x0.var()) / 2)
    return float((x1.mean() - x0.mean()) / pooled) if pooled else np.nan


# ---------------------------------------------------------------- phase 1
def inventory(d: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for name, df in d.items():
        dates = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
        rows.append({
            "table": name, "rows": len(df), "columns": df.shape[1],
            "duplicate_rows": int(df.duplicated().sum()), "duplicate_pk": int(df.iloc[:, 0].duplicated().sum()),
            "null_cells": int(df.isna().sum().sum()),
            "null_columns": "; ".join(f"{c}={n}" for c, n in df.isna().sum().items() if n),
            "date_min": min(df[c].min() for c in dates).date(), "date_max": max(df[c].max() for c in dates).date(),
        })
    s, a = d["subscriptions"], d["accounts"]
    fk = {
        "subscriptions.account_id": (~s.account_id.isin(a.account_id)).sum(),
        "usage.subscription_id": (~d["usage"].subscription_id.isin(s.subscription_id)).sum(),
        "tickets.account_id": (~d["tickets"].account_id.isin(a.account_id)).sum(),
        "events.account_id": (~d["events"].account_id.isin(a.account_id)).sum(),
    }
    inv = pd.DataFrame(rows)
    inv["fk_orphans"] = inv.table.map({"subscriptions": fk["subscriptions.account_id"], "usage": fk["usage.subscription_id"],
                                       "tickets": fk["tickets.account_id"], "events": fk["events.account_id"]}).fillna(0).astype(int)
    return inv


# ---------------------------------------------------------------- phase 5/12 generator recovery
def generator_fit(d: dict[str, pd.DataFrame]) -> pd.DataFrame:
    a, s, u, t, c = d["accounts"], d["subscriptions"], d["usage"], d["tickets"], d["events"]
    s = s.merge(a[["account_id", "signup_date"]], on="account_id")
    rows = []

    def add(field, hypothesis, statistic, p, deciles, verdict):
        rows.append({"field": field, "generator_hypothesis": hypothesis, "ks_statistic": statistic, "ks_p_value": p,
                     "decile_counts": deciles, "verdict": verdict})

    frac = ((s.start_date - s.signup_date).dt.days / (OBS_END - s.signup_date).dt.days.replace(0, np.nan)).dropna()
    ks = stats.kstest(frac.clip(0, 1), "uniform")
    add("subscriptions.start_date", "signup + U(0,1) x (obs_end - signup)", ks.statistic, ks.pvalue,
        np.histogram(frac, 10, (0, 1))[0].tolist(), "CONSISTENT" if ks.pvalue > 0.05 else "REJECTED")
    e = s[s.end_date.notna()]
    room = (OBS_END - e.start_date).dt.days
    frac = ((e.end_date - e.start_date).dt.days / room.replace(0, np.nan)).dropna()
    ks = stats.kstest(frac.clip(0, 1), "uniform")
    add("subscriptions.end_date", "start + U(0,1) x (obs_end - start), for ~9.7% of records", ks.statistic, ks.pvalue,
        np.histogram(frac, 10, (0, 1))[0].tolist(), "CONSISTENT" if ks.pvalue > 0.05 else "REJECTED")
    cc = c.merge(a[["account_id", "signup_date"]], on="account_id")
    frac = (cc.churn_date - cc.signup_date).dt.days / (OBS_END - cc.signup_date).dt.days.replace(0, np.nan)
    ks = stats.kstest(frac.dropna().clip(0, 1), "uniform")
    add("churn_events.churn_date", "signup + U(0,1) x (obs_end - signup)", ks.statistic, ks.pvalue,
        np.histogram(frac.dropna(), 10, (0, 1))[0].tolist(), "CONSISTENT" if ks.pvalue > 0.05 else "REJECTED")
    for field, series in [("feature_usage.usage_date", u.usage_date), ("support_tickets.submitted_at", t.submitted_at)]:
        x = (series - pd.Timestamp("2023-01-01")).dt.days / 730
        ks = stats.kstest(x.clip(0, 1), "uniform")
        add(field, "U(2023-01-01, 2024-12-31), independent of subscription/account dates", ks.statistic, ks.pvalue,
            np.histogram(x, 10, (0, 1))[0].tolist(), "CONSISTENT" if ks.pvalue > 0.05 else "REJECTED")
    k = s.groupby("account_id").size()
    gof = stats.chisquare(k.values)
    rows.append({"field": "subscriptions per account", "generator_hypothesis": "records assigned to accounts at random (multinomial)",
                 "ks_statistic": float(k.var() / k.mean()), "ks_p_value": float(gof.pvalue),
                 "decile_counts": "dispersion index (var/mean) in ks_statistic; chi2 GOF p in ks_p_value",
                 "verdict": "CONSISTENT" if gof.pvalue > 0.05 else "REJECTED"})
    pay = s[~s.is_trial]
    per_seat = (pay.mrr_amount / pay.seats).groupby(pay.plan_tier).agg(["min", "max"])
    rows.append({"field": "subscriptions.mrr_amount", "generator_hypothesis": "seats x fixed price per plan; trial = 0",
                 "ks_statistic": np.nan, "ks_p_value": np.nan,
                 "decile_counts": "; ".join(f"{p}: {r['min']:.0f}-{r['max']:.0f}/seat" for p, r in per_seat.iterrows()),
                 "verdict": "DETERMINISTIC" if (per_seat["min"] == per_seat["max"]).all() else "NOT DETERMINISTIC"})
    return pd.DataFrame(rows)


def end_probability_by_attribute(d: dict[str, pd.DataFrame]) -> pd.DataFrame:
    s = d["subscriptions"].merge(d["accounts"][["account_id", "churn_flag"]].rename(columns={"churn_flag": "account_churn_flag"}), on="account_id")
    s["ended"] = s.end_date.notna()
    rows = []
    for col in ["plan_tier", "billing_frequency", "is_trial", "auto_renew_flag", "upgrade_flag", "downgrade_flag", "account_churn_flag"]:
        ct = pd.crosstab(s[col], s.ended)
        chi, p, *_ = stats.chi2_contingency(ct)
        for level, r in ct.iterrows():
            rows.append({"attribute": col, "level": str(level), "records": int(r.sum()), "ended": int(r.get(True, 0)),
                         "p_end": r.get(True, 0) / r.sum(), "chi2_p_value_attribute": p})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- phase 9/10/11 Q4 under generator null
def expected_ends_under_generator(d: dict[str, pd.DataFrame]) -> pd.DataFrame:
    e = d["subscriptions"][d["subscriptions"].end_date.notna()]
    room = (OBS_END - e.start_date).dt.days
    windows = {"2024-01..09": ("2024-01-01", "2024-09-30"), "2024-10": ("2024-10-01", "2024-10-31"),
               "2024-11": ("2024-11-01", "2024-11-30"), "2024-12": ("2024-12-01", "2024-12-31"),
               "last_7_days": ("2024-12-25", "2024-12-31"), "2024-12-31": ("2024-12-31", "2024-12-31")}
    prior_expected = {"last_7_days": 46.89, "2024-12-31": 6.81}
    rows = []
    for label, (lo, hi) in windows.items():
        lo_d = (pd.Timestamp(lo) - e.start_date).dt.days.clip(lower=0)
        hi_d = np.minimum((pd.Timestamp(hi) - e.start_date).dt.days, room)
        p = ((hi_d - lo_d + 1).clip(lower=0)) / (room + 1)
        observed = int(e.end_date.between(lo, hi).sum())
        expected = float(p.sum())
        rows.append({"window": label, "observed_ends": observed, "expected_under_generator": expected,
                     "observed_expected_ratio": observed / expected,
                     "poisson_two_sided_p": float(min(1, 2 * min(stats.poisson.cdf(observed, expected), stats.poisson.sf(observed - 1, expected)))),
                     "prior_analysis_expected": prior_expected.get(label, np.nan)})
    return pd.DataFrame(rows)


MONTHS = pd.period_range("2024-01", "2024-12", freq="M")
M_START = np.array([p.start_time for p in MONTHS], dtype="datetime64[D]")
M_END = np.array([p.end_time.normalize() for p in MONTHS], dtype="datetime64[D]")
COMPOSITION = ["q4", "log1p_mrr", "log1p_seats", "plan_tier", "billing_frequency", "is_trial", "industry", "country", "referral_source"]
CATEGORICAL = ["plan_tier", "billing_frequency", "industry", "country", "referral_source"]


def person_month(base: pd.DataFrame, st: np.ndarray, en: np.ndarray) -> pd.DataFrame:
    """Vectorised replica of root_cause_triangulation.build_person_month (2024, cutoff 2024-12-31)."""
    st = np.asarray(st, dtype="datetime64[D]")
    en = np.asarray(en, dtype="datetime64[D]")
    has_end = ~np.isnat(en)
    eff = np.where(has_end, en, OBS_D)
    lo = np.maximum(st[:, None], M_START[None, :])
    hi = np.minimum(eff[:, None], M_END[None, :])
    days = (hi - lo).astype(int) + 1
    event = has_end[:, None] & (en[:, None] >= M_START[None, :]) & (en[:, None] <= M_END[None, :])
    i, j = np.nonzero(days > 0)
    df = base.iloc[i][["account_id", "mrr_amount", "seats"] + CATEGORICAL + ["is_trial"]].reset_index(drop=True)
    df["start_cohort_index"] = pd.PeriodIndex(pd.to_datetime(st[i]), freq="M").asi8 - pd.Period("2023-01", "M").ordinal
    df["q4"] = (j >= 9).astype(int)
    df["event"] = event[i, j].astype(int)
    df["exposure_months"] = days[i, j] / 30.4375
    df["month_index"] = j
    df["log1p_mrr"] = np.log1p(df.mrr_amount)
    df["log1p_seats"] = np.log1p(df.seats)
    return df


def fit_q4(df: pd.DataFrame, covariates: list[str]) -> tuple[float, float, float, float]:
    x = pd.get_dummies(df[covariates], columns=[c for c in covariates if c in CATEGORICAL], drop_first=True, dtype=float)
    if "is_trial" in x:
        x["is_trial"] = x["is_trial"].astype(float)
    x.insert(0, "intercept", 1.0)
    r = GLM(df["event"], x, family=Poisson(), offset=np.log(df["exposure_months"])).fit(
        cov_type="cluster", cov_kwds={"groups": df["account_id"]})
    k = x.columns.get_loc("q4")
    lo, hi = r.conf_int().iloc[k]
    return math.exp(r.params.iloc[k]), math.exp(lo), math.exp(hi), float(r.pvalues.iloc[k])


Q4_MODELS = {
    "UNADJUSTED": (lambda df: df, ["q4"]),
    "COMPOSITION_PLUS_START_COHORT": (lambda df: df, COMPOSITION + ["start_cohort_index"]),
    "EXCLUDE_DECEMBER_PLUS_START_COHORT": (lambda df: df[df.month_index != 11], COMPOSITION + ["start_cohort_index"]),
}


def simulate_dates(rng: np.random.Generator, signup: np.ndarray, p_end: float) -> tuple[np.ndarray, np.ndarray]:
    st = signup + rng.integers(0, (OBS_D - signup).astype(int) + 1).astype("timedelta64[D]")
    ended = rng.random(len(st)) < p_end
    en = st + rng.integers(0, (OBS_D - st).astype(int) + 1).astype("timedelta64[D]")
    return st, np.where(ended, en, np.datetime64("NaT", "D"))


def q4_null_calibration(d: dict[str, pd.DataFrame], sims: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    a = d["accounts"]
    base = d["subscriptions"].merge(a[["account_id", "signup_date", "industry", "country", "referral_source"]], on="account_id")
    observed_pm = person_month(base, base.start_date.values, base.end_date.values)
    observed = {m: fit_q4(f(observed_pm), cov) for m, (f, cov) in Q4_MODELS.items()}
    rng = np.random.default_rng(SEED)
    signup = base.signup_date.values.astype("datetime64[D]")
    p_end = base.end_date.notna().mean()
    draws = []
    for b in range(sims):
        st, en = simulate_dates(rng, signup, p_end)
        pm = person_month(base, st, en)
        row = {"sim": b, "ends_31_12": int((en == OBS_D).sum()),
               "ends_q4": int((en >= np.datetime64("2024-10-01")).sum()),
               "ends_dec": int((en >= np.datetime64("2024-12-01")).sum())}
        for m, (f, cov) in Q4_MODELS.items():
            irr, _, _, p = fit_q4(f(pm), cov)
            row[f"{m}_irr"], row[f"{m}_p"] = irr, p
        draws.append(row)
    draws = pd.DataFrame(draws)
    obs_counts = {"ends_31_12": int((base.end_date == OBS_END).sum()), "ends_q4": int((base.end_date >= "2024-10-01").sum()),
                  "ends_dec": int((base.end_date >= "2024-12-01").sum())}
    rows = []
    for m in Q4_MODELS:
        irr, lo, hi, p = observed[m]
        sim_irr, sim_p = draws[f"{m}_irr"], draws[f"{m}_p"]
        rows.append({"statistic": f"IRR_Q4_{m}", "observed": irr, "observed_ci95": f"{lo:.3f}-{hi:.3f}", "observed_p": p,
                     "null_mean": sim_irr.mean(), "null_p2_5": sim_irr.quantile(.025), "null_p97_5": sim_irr.quantile(.975),
                     "observed_percentile_in_null": (sim_irr < irr).mean(),
                     "null_share_significant_positive": ((sim_p < .05) & (sim_irr > 1)).mean(),
                     "excess_over_null_ratio": irr / sim_irr.mean()})
    for k, v in obs_counts.items():
        rows.append({"statistic": k, "observed": v, "observed_ci95": "", "observed_p": np.nan,
                     "null_mean": draws[k].mean(), "null_p2_5": draws[k].quantile(.025), "null_p97_5": draws[k].quantile(.975),
                     "observed_percentile_in_null": (draws[k] < v).mean(), "null_share_significant_positive": np.nan,
                     "excess_over_null_ratio": v / draws[k].mean()})
    return pd.DataFrame(rows), draws


# ---------------------------------------------------------------- phase 2/3 outcome reconstruction
def account_outcomes(d: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    a, s, c = d["accounts"], d["subscriptions"], d["events"]
    days = pd.date_range("2023-01-01", OBS_END).values
    rows = []
    for acc, g in s.groupby("account_id"):
        st = g.start_date.values
        en = g.end_date.fillna(OBS_END + pd.Timedelta(days=1)).values
        active = ((st[None, :] <= days[:, None]) & (en[None, :] > days[:, None])).sum(1)
        first = int(np.argmax(active > 0))
        after = active[first:] == 0
        spells, run = [], 0
        for z in after:
            if z:
                run += 1
            elif run:
                spells.append(run)
                run = 0
        if run:
            spells.append(run)
        rows.append({"account_id": acc, "subscriptions": len(g), "active_at_obs_end": int(g.end_date.isna().sum()),
                     "ended_subscriptions": int(g.end_date.notna().sum()), "zero_active_spells": len(spells),
                     "zero_active_days": int(sum(spells)), "zero_at_obs_end": bool(after[-1]),
                     "all_subscriptions_ended": bool(g.end_date.notna().all())})
    acc = pd.DataFrame(rows).merge(a[["account_id", "churn_flag"]], on="account_id")
    acc["has_churn_event"] = acc.account_id.isin(c.account_id)
    acc["n_churn_events"] = acc.account_id.map(c.groupby("account_id").size()).fillna(0).astype(int)
    defs = [
        ("ACCOUNT_CHURN_FLAG", acc.churn_flag),
        ("ANY_CHURN_EVENT", acc.has_churn_event),
        ("ANY_SUBSCRIPTION_END", acc.ended_subscriptions > 0),
        ("TEMPORARY_ZERO_ACTIVE_SUBSCRIPTIONS", acc.zero_active_spells > 0),
        ("FULL_ACCOUNT_INACTIVE (zero active at 2024-12-31)", acc.zero_at_obs_end),
        ("ALL_SUBSCRIPTIONS_ENDED", acc.all_subscriptions_ended),
    ]
    summary = []
    for name, flag in defs:
        summary.append({"definition": name, "accounts": int(flag.sum()), "rate": flag.mean(),
                        "overlap_with_churn_flag": int((flag & acc.churn_flag).sum()),
                        "overlap_with_any_event": int((flag & acc.has_churn_event).sum())})
    coh = stats.mannwhitneyu(acc.loc[acc.churn_flag, "n_churn_events"], acc.loc[~acc.churn_flag, "n_churn_events"])
    summary.append({"definition": "COHERENCE churn_flag vs n_churn_events (MWU p)", "accounts": np.nan, "rate": coh.pvalue,
                    "overlap_with_churn_flag": np.nan, "overlap_with_any_event": np.nan})
    return pd.DataFrame(summary), acc


# ---------------------------------------------------------------- phase 13 lifecycle links vs chance
def lifecycle_links_vs_chance(d: dict[str, pd.DataFrame], sims: int) -> pd.DataFrame:
    a, s, c = d["accounts"], d["subscriptions"], d["events"]
    s = s.merge(a[["account_id", "signup_date"]], on="account_id").reset_index(drop=True)
    groups = [g.index.values for _, g in s.groupby("account_id")]

    def nearby_share(st, en):
        counts = []
        for idx in groups:
            sst, een = st[idx], en[idx]
            for k in np.where(~np.isnat(een))[0]:
                m = np.abs((sst - een[k]).astype(int)) <= 30
                m[k] = False
                counts.append(m.sum())
        counts = np.array(counts)
        return (counts == 1).mean(), (counts == 0).mean(), (counts >= 2).mean()

    rng = np.random.default_rng(SEED + 1)
    signup = s.signup_date.values.astype("datetime64[D]")
    obs = nearby_share(s.start_date.values.astype("datetime64[D]"), s.end_date.values.astype("datetime64[D]"))
    null = np.array([nearby_share(*simulate_dates(rng, signup, s.end_date.notna().mean())) for _ in range(sims)])
    rows = []
    for i, label in enumerate(["end with exactly 1 start within +-30d (prior: lifecycle move candidate)",
                               "end with 0 starts within +-30d", "end with >=2 starts within +-30d (prior: ambiguous)"]):
        rows.append({"test": label, "observed_share": obs[i], "null_mean": null[:, i].mean(),
                     "null_p2_5": np.percentile(null[:, i], 2.5), "null_p97_5": np.percentile(null[:, i], 97.5),
                     "observed_percentile_in_null": (null[:, i] < obs[i]).mean()})
    # churn events with a subscription end within +-7d (prior: contract-supported)
    prior = OUTPUTS / "outcome_reconciliation" / "event_contract_alignment.csv"
    valid = pd.read_csv(prior, parse_dates=["churn_date"])
    valid = valid[valid.event_taxonomy == "VALID_CHURN_TRANSITION"].merge(a[["account_id", "signup_date"]], on="account_id")
    ends = {k: g.end_date.dropna().values.astype("datetime64[D]") for k, g in s.groupby("account_id")}

    def supported(dates):
        return sum(int((np.abs((ends[acc] - dt).astype(int)) <= 7).any()) for dt, acc in zip(dates, valid.account_id.values))

    o = supported(valid.churn_date.values.astype("datetime64[D]"))
    sg = valid.signup_date.values.astype("datetime64[D]")
    null = np.array([supported(sg + rng.integers(0, (OBS_D - sg).astype(int) + 1).astype("timedelta64[D]")) for _ in range(sims)])
    rows.append({"test": f"valid churn events with subscription end within +-7d (n={len(valid)})", "observed_share": o / len(valid),
                 "null_mean": null.mean() / len(valid), "null_p2_5": np.percentile(null, 2.5) / len(valid),
                 "null_p97_5": np.percentile(null, 97.5) / len(valid), "observed_percentile_in_null": (null < o).mean()})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- phases 6/7/8/14/15/16 independence scan
def independence_scan(d: dict[str, pd.DataFrame], acc_out: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    a, s, u, t, c = d["accounts"], d["subscriptions"].copy(), d["usage"], d["tickets"], d["events"]
    rows = []

    def rec(family, outcome, var, p, n1, n0, effect, note=""):
        rows.append({"family": family, "outcome": outcome, "variable": var, "p_value": p, "n_pos": n1, "n_neg": n0,
                     "effect_smd_or_cramers_v": effect, "note": note})

    def mwu(family, outcome, var, x1, x0, note=""):
        x1, x0 = x1.dropna(), x0.dropna()
        rec(family, outcome, var, stats.mannwhitneyu(x1, x0).pvalue, len(x1), len(x0), smd(x1, x0), note)

    def chi(family, outcome, var, table, note=""):
        c2, p, _, ex = stats.chi2_contingency(table)
        v = math.sqrt(c2 / (table.values.sum() * (min(table.shape) - 1)))
        rec(family, outcome, var, p, np.nan, np.nan, v, f"{note} min_expected={ex.min():.1f}".strip())

    s["ended"] = s.end_date.notna()
    ug = u.groupby("subscription_id").agg(usage_rows=("usage_id", "size"), usage_count=("usage_count", "sum"),
                                          duration=("usage_duration_secs", "sum"), errors=("error_count", "sum"),
                                          features=("feature_name", "nunique"), beta_share=("is_beta_feature", "mean"))
    ug["error_rate"] = ug.errors / ug.usage_count.replace(0, np.nan)
    S = s.set_index("subscription_id").join(ug)
    for v in ug.columns:
        mwu("PRODUCT_ALL_HISTORY", "SUBSCRIPTION_END", v, S.loc[S.ended, v], S.loc[~S.ended, v], "no temporal filter: falsification (leakage allowed)")
    acc = a.set_index("account_id").join(acc_out.set_index("account_id")[["has_churn_event", "n_churn_events", "ended_subscriptions"]])
    acc = acc.join(s.groupby("account_id").agg(n_subs=("subscription_id", "size"), mrr_total=("mrr_amount", "sum"),
                                               mrr_median=("mrr_amount", "median"), trial_share=("is_trial", "mean"),
                                               upgrade_share=("upgrade_flag", "mean"), downgrade_share=("downgrade_flag", "mean"),
                                               annual_share=("billing_frequency", lambda x: (x == "annual").mean()),
                                               autorenew_share=("auto_renew_flag", "mean")))
    acc = acc.join(u.merge(s[["subscription_id", "account_id"]]).groupby("account_id").agg(
        usage_rows=("usage_id", "size"), usage_count=("usage_count", "sum"), errors=("error_count", "sum"), features=("feature_name", "nunique")))
    acc = acc.join(t.groupby("account_id").agg(
        tickets=("ticket_id", "size"), resolution_h=("resolution_time_hours", "mean"), first_response_min=("first_response_time_minutes", "mean"),
        escalations=("escalation_flag", "sum"), csat_mean=("satisfaction_score", "mean"),
        csat_missing_share=("satisfaction_score", lambda x: x.isna().mean()), urgent_share=("priority", lambda x: (x == "urgent").mean())))
    acc[["tickets", "escalations"]] = acc[["tickets", "escalations"]].fillna(0)
    acc["tenure_days"] = (OBS_END - acc.signup_date).dt.days
    numeric = ["seats", "n_subs", "mrr_total", "mrr_median", "trial_share", "upgrade_share", "downgrade_share", "annual_share",
               "autorenew_share", "usage_rows", "usage_count", "errors", "features", "tickets", "resolution_h",
               "first_response_min", "escalations", "csat_mean", "csat_missing_share", "urgent_share", "tenure_days"]
    for outcome in ["churn_flag", "has_churn_event"]:
        y = acc[outcome].astype(bool)
        for v in numeric:
            mwu("ACCOUNT_ALL_HISTORY", outcome, v, acc.loc[y, v], acc.loc[~y, v])
        for v in ["industry", "country", "referral_source", "plan_tier", "is_trial"]:
            chi("ACCOUNT_SEGMENT", outcome, v, pd.crosstab(acc[v], y))
    for v in ["n_churn_events", "ended_subscriptions"]:
        mwu("OUTCOME_COHERENCE", "churn_flag", v, acc.loc[acc.churn_flag, v], acc.loc[~acc.churn_flag, v])
    for v1, v2 in [("plan_tier", "is_trial"), ("plan_tier", "referral_source"), ("industry", "plan_tier")]:
        chi("ACCOUNT_INTERACTION", "churn_flag", f"{v1} x {v2}", pd.crosstab(acc[v1].astype(str) + "|" + acc[v2].astype(str), acc.churn_flag))
    for v1, v2 in [("plan_tier", "billing_frequency"), ("plan_tier", "is_trial"), ("billing_frequency", "auto_renew_flag")]:
        chi("SUBSCRIPTION_INTERACTION", "SUBSCRIPTION_END", f"{v1} x {v2}", pd.crosstab(s[v1].astype(str) + "|" + s[v2].astype(str), s.ended))
    tt = t.merge(acc[["churn_flag", "has_churn_event"]], left_on="account_id", right_index=True)
    for outcome in ["churn_flag", "has_churn_event"]:
        chi("SUPPORT_TICKET", outcome, "csat_missing (NO_RESPONSE vs responded)", pd.crosstab(tt.satisfaction_score.isna(), tt[outcome]))
        for v in ["resolution_time_hours", "first_response_time_minutes", "satisfaction_score"]:
            mwu("SUPPORT_TICKET", outcome, v, tt.loc[tt[outcome], v], tt.loc[~tt[outcome], v], "ticket grain; descriptive")
    ce = c.merge(acc[["plan_tier", "industry", "seats", "tickets", "csat_mean", "errors", "mrr_total"]], left_on="account_id", right_index=True)
    for v in ["plan_tier", "industry"]:
        chi("REASON_CODE", "reason_code", v, pd.crosstab(ce.reason_code, ce[v]))
    chi("REASON_CODE", "reason_code", "feedback_text", pd.crosstab(ce.reason_code, ce.feedback_text.fillna("NO_FEEDBACK")))
    chi("REASON_CODE", "reason_code", "calendar_quarter", pd.crosstab(ce.reason_code, ce.churn_date.dt.to_period("Q").astype(str)))
    for v in ["seats", "tickets", "csat_mean", "errors", "mrr_total", "refund_amount_usd"]:
        rec("REASON_CODE", "reason_code", v, stats.kruskal(*[g[v].dropna() for _, g in ce.groupby("reason_code")]).pvalue, len(ce), 0, np.nan, "Kruskal")
    for label, mask, v in [("reason=support", ce.reason_code == "support", "tickets"), ("reason=support", ce.reason_code == "support", "csat_mean"),
                           ("reason=features", ce.reason_code == "features", "errors"),
                           ("reason=pricing|budget", ce.reason_code.isin(["pricing", "budget"]), "mrr_total")]:
        mwu("REASON_COHERENCE", label, v, ce.loc[mask, v], ce.loc[~mask, v])
    internal = [
        ("support: priority -> resolution_time", stats.kruskal(*[g.resolution_time_hours for _, g in t.groupby("priority")]).pvalue),
        ("support: priority -> first_response", stats.kruskal(*[g.first_response_time_minutes for _, g in t.groupby("priority")]).pvalue),
        ("support: escalation -> resolution_time", stats.mannwhitneyu(t[t.escalation_flag].resolution_time_hours, t[~t.escalation_flag].resolution_time_hours).pvalue),
        ("support: csat ~ resolution_time (spearman)", stats.spearmanr(t.satisfaction_score, t.resolution_time_hours, nan_policy="omit").pvalue),
        ("support: csat ~ first_response (spearman)", stats.spearmanr(t.satisfaction_score, t.first_response_time_minutes, nan_policy="omit").pvalue),
        ("usage: error_count ~ usage_count (spearman)", stats.spearmanr(u.error_count, u.usage_count).pvalue),
        ("events: preceding_upgrade_flag vs real upgrade record in 90d", np.nan),
    ]
    cu = c.merge(s[s.upgrade_flag][["account_id", "start_date"]], on="account_id", how="left")
    cu["hit"] = cu.start_date.between(cu.churn_date - pd.Timedelta(days=90), cu.churn_date)
    real = cu.groupby("churn_event_id").hit.any()
    ct = pd.crosstab(c.set_index("churn_event_id").preceding_upgrade_flag, real)
    internal[-1] = (internal[-1][0], stats.chi2_contingency(ct)[1])
    so = s.sort_values(["account_id", "start_date"]).copy()
    rank = {"Basic": 0, "Pro": 1, "Enterprise": 2}
    so["direction"] = np.sign(so.plan_tier.map(rank) - so.groupby("account_id").plan_tier.shift().map(rank))
    internal.append(("subscriptions: upgrade_flag vs plan direction vs previous record", stats.chi2_contingency(pd.crosstab(so.upgrade_flag, so.direction))[1]))
    internal.append(("subscriptions: plan_tier vs account plan_tier", stats.chi2_contingency(pd.crosstab(s.plan_tier, s.account_id.map(a.set_index("account_id").plan_tier)))[1]))
    internal_df = pd.DataFrame(internal, columns=["internal_coherence_test", "p_value"])
    internal_df["reading"] = np.where(internal_df.p_value < 0.05, "LINKED", "INDEPENDENT (no detectable link)")
    res = pd.DataFrame(rows)
    res["q_value_global_bh"] = multipletests(res.p_value, method="fdr_bh")[1]
    return res.sort_values("p_value").reset_index(drop=True), internal_df


def power_table() -> pd.DataFrame:
    tp = TTestIndPower()
    designs = [
        ("ANALYSIS-09 usage: churned vs strict controls", 325, 135),
        ("ANALYSIS-11B risk-set pairs with telemetry at T-30 (~17% of 486)", 85, 99),
        ("ANALYSIS-10 support: accounts with valid pre-reference tickets (approx.)", 150, 60),
        ("AUDIT subscription grain, all history", 486, 4514),
        ("AUDIT account churn_flag", 110, 390),
        ("AUDIT account any churn event", 352, 148),
    ]
    rows = []
    for label, n1, n0 in designs:
        rows.append({"design": label, "n_outcome": n1, "n_comparison": n0,
                     "mde_cohen_d_alpha_05": tp.solve_power(nobs1=n1, ratio=n0 / n1, alpha=0.05, power=0.8),
                     "mde_cohen_d_alpha_bonferroni_40": tp.solve_power(nobs1=n1, ratio=n0 / n1, alpha=0.05 / 40, power=0.8)})
    return pd.DataFrame(rows)


def telemetry_classes(d: dict[str, pd.DataFrame]) -> pd.DataFrame:
    s, u = d["subscriptions"].copy(), d["usage"]
    g = u.groupby("subscription_id").usage_count.sum()
    s["telemetry_class"] = np.select([~s.subscription_id.isin(g.index), s.subscription_id.map(g).fillna(0) == 0],
                                     ["NO_TELEMETRY", "ZERO_OBSERVED_USAGE"], "OBSERVED_USAGE")
    uu = u.merge(s[["subscription_id", "start_date", "end_date"]], on="subscription_id")
    inlife = (uu.usage_date >= uu.start_date) & (uu.end_date.isna() | (uu.usage_date <= uu.end_date))
    life = (s.end_date.fillna(OBS_END) - s.start_date).dt.days + 1
    expected_inlife = (s.subscription_id.map(u.groupby("subscription_id").size()).fillna(0) * life / 731).sum()
    out = s.groupby(["telemetry_class", s.end_date.notna().rename("ended")]).size().rename("subscriptions").reset_index()
    out.loc[len(out)] = ["IN_LIFETIME_USAGE_ROWS_OBSERVED", np.nan, int(inlife.sum())]
    out.loc[len(out)] = ["IN_LIFETIME_USAGE_ROWS_EXPECTED_IF_DATES_INDEPENDENT", np.nan, round(float(expected_inlife), 1)]
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sims", type=int, default=1000)
    parser.add_argument("--link-sims", type=int, default=200)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    d = load()
    outputs = {"raw_inventory.csv": inventory(d), "generator_fit.csv": generator_fit(d),
               "end_probability_by_attribute.csv": end_probability_by_attribute(d),
               "expected_ends_under_generator.csv": expected_ends_under_generator(d)}
    summary, acc_out = account_outcomes(d)
    outputs["account_outcome_definitions.csv"] = summary
    outputs["account_activity_timeline_summary.csv"] = acc_out
    outputs["lifecycle_links_vs_chance.csv"] = lifecycle_links_vs_chance(d, args.link_sims)
    scan, internal = independence_scan(d, acc_out)
    outputs["independence_scan.csv"] = scan
    outputs["internal_coherence.csv"] = internal
    outputs["power_mde.csv"] = power_table()
    outputs["telemetry_classes.csv"] = telemetry_classes(d)
    q4, draws = q4_null_calibration(d, args.sims)
    outputs["q4_null_calibration.csv"] = q4
    outputs["q4_null_draws.csv"] = draws
    for name, df in outputs.items():
        df.to_csv(OUT / name, index=False)
    meta = {"analysis_id": "INDEPENDENT-AUDIT-01", "seed": SEED, "null_simulations": args.sims, "link_simulations": args.link_sims,
            "observation_end": str(OBS_END.date()), "tests_in_scan": int(len(scan)),
            "scan_p_lt_05": int((scan.p_value < .05).sum()), "scan_q_lt_10": int((scan.q_value_global_bh < .10).sum()),
            "scan_pvalues_ks_vs_uniform_p": float(stats.kstest(scan.p_value, "uniform").pvalue),
            "outputs": sorted(outputs)}
    (OUT / "analysis_metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps(meta, indent=2))
    print(q4.round(3).to_string())


if __name__ == "__main__":
    main()
