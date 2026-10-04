"""ANALYSIS-15 — Analyses that the blocked environment made impossible.

Until 2026-10-04, Windows Smart App Control blocked `sklearn.ensemble` and
`statsmodels.tsa` (and therefore `statsmodels.api`). Earlier pipelines avoided
those modules. This script runs the three analysis families that were never
executed because of the block:

1. Time series (statsmodels.tsa): trend, Q4 shift with HAC errors, STL seasonality,
   ADF stationarity and CUSUM structural-break tests on exposure-normalised monthly
   series, plus the observed-minus-mechanism residual of subscription ends.
2. Ensemble models (sklearn.ensemble): random forest and gradient boosting with the
   full 40-feature usage/error matrix, cross-validated, each against its own
   permutation null.
3. Cluster-aware multivariable inference (statsmodels.api GEE): subscription end on
   every antecedent from the five tables at once, exchangeable within account.

Run: python solution/scripts/unblocked_models.py
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from statsmodels.stats.diagnostic import breaks_cusumolsresid
from statsmodels.stats.multitest import multipletests
from statsmodels.tsa.seasonal import STL
from statsmodels.tsa.stattools import adfuller

from end_to_end_sweep import account_master, load, monthly_kpis

warnings.filterwarnings("ignore")
from _paths import OUTPUTS, PKG, RAW_DIR, ROOT  # noqa: E402,F401  (package paths)
OUT = OUTPUTS / "unblocked_models"
OBS_END = pd.Timestamp("2024-12-31")
SEED = 20261004


# ------------------------------------------------------------------ 1. time series
def expected_monthly_ends(s: pd.DataFrame) -> pd.Series:
    """Expected ends per month under the recovered mechanism (end ~ U[start, obs_end]), conditional on observed ended records."""
    e = s[s.end_date.notna()]
    room = (OBS_END - e.start_date).dt.days
    out = {}
    for p in pd.period_range("2023-01", "2024-12", freq="M"):
        lo = (p.start_time - e.start_date).dt.days.clip(lower=0)
        hi = np.minimum((p.end_time.normalize() - e.start_date).dt.days, room)
        out[str(p)] = float((((hi - lo + 1).clip(lower=0)) / (room + 1)).sum())
    return pd.Series(out)


def time_series(d: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    m = monthly_kpis(d).set_index("month")
    m["expected_ends_mechanism"] = expected_monthly_ends(d["subscriptions"])
    m["ends_minus_mechanism"] = m.ended_subscriptions - m.expected_ends_mechanism
    m["ends_ratio_to_mechanism"] = m.ended_subscriptions / m.expected_ends_mechanism.replace(0, np.nan)
    series = {
        "churn_events_per_100_accounts": "CEO view (events, account denominator)",
        "ended_subs_per_100_active": "subscription ends per 100 exposed records",
        "ends_minus_mechanism": "observed ends minus recovered-mechanism expectation",
        "usage_per_active_account": "Product view (usage, active-account denominator)",
        "usage_count": "Product view (raw usage volume)",
        "tickets_per_100_accounts": "support load per 100 accounts",
        "csat_mean": "CS view (CSAT)",
        "csat_response_rate": "CSAT response rate",
        "error_rate": "product error rate",
    }
    rows = []
    for col, label in series.items():
        y = m[col].astype(float)
        # 2023H1 has very few accounts/subscriptions: report both full window and 2023-07 onward
        for window, yy in [("2023-01..2024-12", y), ("2023-07..2024-12", y.loc["2023-07":])]:
            yy = yy.dropna()
            t = np.arange(len(yy))
            q4_2024 = np.array([1 if mth >= "2024-10" else 0 for mth in yy.index])
            X = sm.add_constant(np.column_stack([t, q4_2024]))
            hac = sm.OLS(yy.values, X).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
            trend_only = sm.OLS(yy.values, sm.add_constant(t)).fit()
            cusum_stat, cusum_p, _ = breaks_cusumolsresid(trend_only.resid, ddof=2)
            try:
                adf_p = adfuller(yy.values, maxlag=2, autolag=None)[1]
            except Exception:
                adf_p = np.nan
            seasonal_strength = np.nan
            if window == "2023-01..2024-12":
                stl = STL(yy.values, period=12, robust=True).fit()
                denom = np.var(stl.seasonal + stl.resid)
                seasonal_strength = max(0.0, 1 - np.var(stl.resid) / denom) if denom > 0 else np.nan
            rows.append({"series": col, "meaning": label, "window": window, "months": len(yy),
                         "first_value": yy.iloc[0], "last_value": yy.iloc[-1],
                         "trend_per_month": hac.params[1], "trend_p_hac": hac.pvalues[1],
                         "q4_2024_shift": hac.params[2], "q4_2024_shift_p_hac": hac.pvalues[2],
                         "adf_p_value": adf_p, "cusum_break_p": cusum_p, "stl_seasonal_strength_period12": seasonal_strength})
    out = pd.DataFrame(rows)
    out["q4_shift_q_bh"] = multipletests(out.q4_2024_shift_p_hac.fillna(1), method="fdr_bh")[1]
    return out, m.reset_index()


# ------------------------------------------------------------------ 2. ensemble models with full feature matrix
def feature_matrix(d: dict[str, pd.DataFrame], m: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, list[str], list[str]]:
    s, u = d["subscriptions"], d["feature_usage"]
    use_w = u.pivot_table(index="subscription_id", columns="feature_name", values="usage_count", aggfunc="sum", fill_value=0).add_prefix("use_")
    err_w = u.pivot_table(index="subscription_id", columns="feature_name", values="error_count", aggfunc="sum", fill_value=0).add_prefix("err_")
    sub = s.set_index("subscription_id").join(use_w).join(err_w)
    feat_cols = list(use_w.columns) + list(err_w.columns)
    sub[feat_cols] = sub[feat_cols].fillna(0)
    sub["no_telemetry"] = (~sub.index.isin(u.subscription_id)).astype(float)
    sub = sub.join(m[["industry", "country", "referral_source", "seats", "tickets", "csat_mean", "ticket_escalations", "ticket_resolution_h",
                      "ticket_first_response_min", "csat_no_response_share"]].rename(columns={"seats": "account_seats"}), on="account_id")
    sub["start_month_index"] = (sub.start_date.dt.year - 2023) * 12 + sub.start_date.dt.month
    acc_use = u.merge(s[["subscription_id", "account_id"]]).pivot_table(index="account_id", columns="feature_name", values="usage_count",
                                                                        aggfunc="sum", fill_value=0).add_prefix("use_")
    acc_err = u.merge(s[["subscription_id", "account_id"]]).pivot_table(index="account_id", columns="feature_name", values="error_count",
                                                                        aggfunc="sum", fill_value=0).add_prefix("err_")
    acc = m.join(acc_use).join(acc_err)
    acc[feat_cols] = acc[feat_cols].fillna(0)
    return sub, acc, feat_cols, list(use_w.columns)


def ensemble_tests(d: dict[str, pd.DataFrame], m: pd.DataFrame, n_perm: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    sub, acc, feat_cols, _ = feature_matrix(d, m)
    sub_cat = ["plan_tier", "billing_frequency", "industry", "country", "referral_source"]
    sub_num = ["seats", "mrr_amount", "account_seats", "tickets", "csat_mean", "ticket_escalations", "ticket_resolution_h",
               "ticket_first_response_min", "csat_no_response_share", "start_month_index", "no_telemetry"] + feat_cols
    sub_bool = ["is_trial", "upgrade_flag", "downgrade_flag", "auto_renew_flag"]
    acc_cat = ["industry", "country", "referral_source", "plan_tier", "signup_half"]
    acc_num = ["seats", "tenure_years", "subs_total", "sub_mrr_median", "sub_trial_share", "sub_upgrade_share", "sub_downgrade_share",
               "sub_annual_share", "sub_autorenew_share", "usage_count", "usage_errors", "usage_features", "usage_active_days", "tickets",
               "ticket_resolution_h", "ticket_first_response_min", "ticket_escalations", "ticket_urgent_high_share", "csat_mean",
               "csat_no_response_share"] + feat_cols
    tasks = []
    SX = sub[sub_cat + sub_num + sub_bool].copy(); SX[sub_bool] = SX[sub_bool].astype(float)
    AX = acc[acc_cat + acc_num + ["is_trial"]].copy(); AX["is_trial"] = AX["is_trial"].astype(float)
    tasks.append(("subscription", "subscription_end", SX, sub.end_date.notna().astype(int).values, sub_cat, sub_num + sub_bool))
    tasks.append(("account", "churn_flag", AX, acc.churn_flag.astype(int).values, acc_cat, acc_num + ["is_trial"]))
    tasks.append(("account", "has_churn_event", AX, acc.has_churn_event.astype(int).values, acc_cat, acc_num + ["is_trial"]))
    rng = np.random.default_rng(SEED)
    rows, imp_rows = [], []
    for grain, outcome, X, y, cat, num in tasks:
        pre = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore"), cat),
                                 ("num", make_pipeline(SimpleImputer(strategy="median"), StandardScaler()), num)])
        models = {
            "random_forest": make_pipeline(pre, RandomForestClassifier(n_estimators=300, min_samples_leaf=5, max_features="sqrt",
                                                                       n_jobs=-1, random_state=SEED)),
            "gradient_boosting": make_pipeline(pre, HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=200,
                                                                                   random_state=SEED)),
        }
        for name, model in models.items():
            seed_aucs = []
            for cv_seed in range(5):
                pred = cross_val_predict(model, X, y, cv=StratifiedKFold(5, shuffle=True, random_state=cv_seed), method="predict_proba")[:, 1]
                seed_aucs.append(roc_auc_score(y, pred))
            cv = StratifiedKFold(5, shuffle=True, random_state=SEED)
            obs = roc_auc_score(y, cross_val_predict(model, X, y, cv=cv, method="predict_proba")[:, 1])
            null = [roc_auc_score(yp, cross_val_predict(model, X, yp, cv=cv, method="predict_proba")[:, 1])
                    for yp in (rng.permutation(y) for _ in range(n_perm))]
            rows.append({"grain": grain, "outcome": outcome, "model": name, "n": len(y), "features_in": X.shape[1], "prevalence": y.mean(),
                         "oof_auc_5_cv_seeds_mean": np.mean(seed_aucs), "oof_auc_5_cv_seeds_min": np.min(seed_aucs),
                         "oof_auc_5_cv_seeds_max": np.max(seed_aucs), "oof_auc_reference_split": obs,
                         "null_auc_mean": np.mean(null), "null_auc_p97_5": np.percentile(null, 97.5),
                         "permutation_p": (1 + sum(np.array(null) >= obs)) / (n_perm + 1)})
            if name == "random_forest":
                model.fit(X, y)
                names = model[0].get_feature_names_out()
                imp = pd.Series(model[-1].feature_importances_, index=names).sort_values(ascending=False)
                for rank, (f, v) in enumerate(imp.head(15).items(), 1):
                    imp_rows.append({"grain": grain, "outcome": outcome, "rank": rank, "feature": f, "impurity_importance": v})
    return pd.DataFrame(rows), pd.DataFrame(imp_rows)


# ------------------------------------------------------------------ 3. GEE multivariable, clustered by account
def gee_subscription_end(d: dict[str, pd.DataFrame], m: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    s, u = d["subscriptions"], d["feature_usage"]
    ug = u.groupby("subscription_id").agg(sub_usage=("usage_count", "sum"), sub_errors=("error_count", "sum"), sub_features=("feature_name", "nunique"))
    df = s.join(ug, on="subscription_id").join(
        m[["industry", "country", "referral_source", "tickets", "csat_mean", "ticket_escalations", "csat_no_response_share"]], on="account_id")
    df["ended"] = df.end_date.notna().astype(int)
    df["log_mrr"] = np.log1p(df.mrr_amount); df["log_seats"] = np.log1p(df.seats)
    df["log_usage"] = np.log1p(df.sub_usage.fillna(0)); df["log_errors"] = np.log1p(df.sub_errors.fillna(0))
    df["no_telemetry"] = df.sub_usage.isna().astype(int)
    df["csat_missing_all"] = df.csat_mean.isna().astype(int); df["csat_mean_f"] = df.csat_mean.fillna(df.csat_mean.mean())
    df["start_half"] = df.start_date.dt.year.astype(str) + np.where(df.start_date.dt.month <= 6, "H1", "H2")
    for b in ["is_trial", "upgrade_flag", "downgrade_flag", "auto_renew_flag"]:
        df[b] = df[b].astype(int)
    formula = ("ended ~ C(plan_tier) + C(billing_frequency) + is_trial + auto_renew_flag + upgrade_flag + downgrade_flag + log_mrr + log_seats"
               " + C(industry) + C(country) + C(referral_source) + C(start_half) + log_usage + log_errors + sub_features + no_telemetry"
               " + tickets + ticket_escalations + csat_mean_f + csat_missing_all + csat_no_response_share")
    df = df.dropna(subset=["sub_features"]).copy() if False else df.assign(sub_features=df.sub_features.fillna(0))
    model = smf.gee(formula, groups="account_id", data=df, family=sm.families.Binomial(), cov_struct=sm.cov_struct.Exchangeable())
    res = model.fit(maxiter=200)
    terms = res.model.data.design_info.terms
    rows = []
    for term in terms:
        name = term.name()
        if name == "Intercept":
            continue
        cols = [c for c in res.params.index if c == name or c.startswith(name + "[")]
        if not cols:
            continue
        R = np.zeros((len(cols), len(res.params)))
        for i, c in enumerate(cols):
            R[i, list(res.params.index).index(c)] = 1
        w = res.wald_test(R, scalar=True)
        rows.append({"term": name, "df": len(cols), "wald_chi2": float(w.statistic), "p_value": float(w.pvalue),
                     "odds_ratios": "; ".join(f"{c}={np.exp(res.params[c]):.3f}" for c in cols)})
    out = pd.DataFrame(rows)
    out["q_value_bh"] = multipletests(out.p_value, method="fdr_bh")[1]
    meta = {"n": int(len(df)), "accounts": int(df.account_id.nunique()), "events": int(df.ended.sum()),
            "working_correlation": float(res.model.cov_struct.dep_params), "terms": int(len(out))}
    return out.sort_values("p_value"), meta


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    d = load()
    m = account_master(d)
    ts, monthly = time_series(d)
    ens, imp = ensemble_tests(d, m, n_perm=50)
    gee, gee_meta = gee_subscription_end(d, m)
    outputs = {"time_series_tests.csv": ts, "monthly_with_mechanism.csv": monthly, "ensemble_tests.csv": ens,
               "random_forest_top_importance.csv": imp, "gee_subscription_end.csv": gee}
    for name, df in outputs.items():
        df.to_csv(OUT / name, index=False)
    meta = {"analysis_id": "ANALYSIS-15", "seed": SEED, "permutations_per_model": 50, "gee": gee_meta,
            "time_series_q4_shift_q_lt_10": int((ts.q4_shift_q_bh < .10).sum()),
            "ensemble_permutation_p_lt_05": int((ens.permutation_p < .05).sum()),
            "gee_terms_q_lt_10": int((gee.q_value_bh < .10).sum()), "outputs": sorted(outputs)}
    (OUT / "analysis_metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps(meta, indent=2))
    pd.set_option("display.width", 250)
    print(ts.round(4).to_string())
    print(ens.round(3).to_string())
    print(gee.round(4).to_string())


if __name__ == "__main__":
    main()
