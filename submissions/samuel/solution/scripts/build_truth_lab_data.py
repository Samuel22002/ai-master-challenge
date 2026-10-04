"""TRUTH-LAB-BUILD-02 (+ FINAL-CLOSEOUT-TRUTH-LAB-01) — pre-computed data for the static Churn Truth Lab.

All headline numbers are read from the validated outputs (final_numbers.json and
auditor_integration_summary.json). Per-account and per-quarter detail is derived
from the RAW CSVs with the same rules as the validated scripts, and every derived
aggregate that also exists in a validated output is asserted equal before writing.
The browser never recalculates a critical number: it only looks values up.

UI language: Portuguese, pt-BR number format (formatting only — values unchanged).
Canonical labels stay in English (global labels, SOURCE/GRAIN/COVERAGE/LIMITATION).

Writes:
  submission/samuel/solution/truth-lab/data/truth_lab_data.json
  submission/samuel/solution/truth-lab/data/truth_lab_data.js   (same object; file:// pages cannot fetch() JSON)

Run: python solution/scripts/build_truth_lab_data.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from _paths import OUTPUTS, PKG, RAW_DIR, ROOT  # noqa: E402,F401  (package paths)
RAW = RAW_DIR
FINAL = OUTPUTS / "final_rewrite"
AUD = OUTPUTS / "auditor_integration"
SWEEP = OUTPUTS / "end_to_end_sweep"
LAB = PKG / "solution" / "truth-lab" / "data"

MRR_LIMIT = ("MRR proxy — not consolidated revenue. Soma de mrr_amount sobre registros de assinatura sobrepostos; "
             "o dataset não declara moeda.")
STATE_LIMIT = "Observable contract state — commercial semantics not validated."
PRIORITY_LIMIT = "Business priority — not predicted churn risk."
DENOM_PT = ("Conta ativa = conta com ≥ 1 registro de assinatura ativo na data de fim do período "
            "(start_date ≤ fim do período e end_date vazio ou posterior).")
NUMER_PT = "Numerador: todas as linhas de uso datadas no período, sem filtro pela vida da assinatura (só 22,27% caem dentro dela)."


def load():
    a = pd.read_csv(RAW / "ravenstack_accounts.csv", parse_dates=["signup_date"])
    s = pd.read_csv(RAW / "ravenstack_subscriptions.csv", parse_dates=["start_date", "end_date"])
    u = pd.read_csv(RAW / "ravenstack_feature_usage.csv", parse_dates=["usage_date"])
    t = pd.read_csv(RAW / "ravenstack_support_tickets.csv", parse_dates=["submitted_at", "closed_at"])
    c = pd.read_csv(RAW / "ravenstack_churn_events.csv", parse_dates=["churn_date"])
    return a, s, u, t, c


def fmt_int(x: float) -> str:
    return f"{round(x):,}".replace(",", ".")


def fmt_pct(x: float, d: int = 1) -> str:
    return f"{100 * x:.{d}f}%".replace(".", ",")


def main() -> None:
    N = json.loads((FINAL / "final_numbers.json").read_text(encoding="utf-8"))
    S = json.loads((AUD / "auditor_integration_summary.json").read_text(encoding="utf-8"))
    den = json.loads((AUD / "usage_denominator_definition.json").read_text(encoding="utf-8"))
    a, s, u, t, c = load()
    ids = a.account_id
    A = a.set_index("account_id")

    metrics: dict[str, dict] = {}

    def M(mid, value, display, source, grain, coverage, limitation):
        metrics[mid] = {"value": value, "display": display, "source": source, "grain": grain, "coverage": coverage, "limitation": limitation}

    # ---------- churn signals + observable-state check (validated)
    cd = N["churn_definitions"]
    M("def_flag", cd["churn_flag"], str(cd["churn_flag"]), "accounts.churn_flag", "conta", "500 / 500 contas",
      "Sinal de churn sem data nem motivo. As 110 contas flagged ainda possuem registros de subscription ativos com MRR proxy positivo.")
    M("def_event", cd["any_churn_event"], str(cd["any_churn_event"]), "churn_events (600 eventos)", "evento agregado por conta", "500 contas; 600 eventos",
      "Sinal de churn. O vínculo evento–contrato não é maior que o acaso (registro F-04). Inclui reativações.")
    M("def_end", cd["any_subscription_end"], str(cd["any_subscription_end"]), "subscriptions.end_date", "registro de assinatura agregado por conta",
      "500 contas; 486 registros encerrados", "Sinal de churn. Fim de assinatura não é perda de cliente: 98,7% do MRR proxy encerrado em 2024 estava em contas com outro registro ativo logo depois.")
    M("def_zero", cd["zero_active_records_2024_12_31"], str(cd["zero_active_records_2024_12_31"]), "subscriptions (start_date, end_date)",
      "conta, em 31/12/2024", "500 / 500 contas",
      "Checagem de estado observável no fim da observação, não um sinal de churn. " + STATE_LIMIT + " Não significa ausência de perda real: o estado contratual observável não permite identificar de forma confiável perda completa da conta.")
    for mid, k, lab in [("ov_fe", "flag_and_event", "flag ∩ evento"), ("ov_fn", "flag_and_end", "flag ∩ fim"), ("ov_en", "event_and_end", "evento ∩ fim"), ("ov_all", "all_three", "os três")]:
        M(mid, cd[k], str(cd[k]), "accounts, churn_events, subscriptions", "conta", "500 contas", f"Sobreposição inclusiva ({lab}); os sinais não são intercambiáveis.")
    M("conf_outcome", None, "RED", "accounts, churn_events, subscriptions", "conta", "500 contas",
      "No reconciled customer-loss target. Sem target reconciliado de perda de cliente: 110 / 352 / 312 são três populações de churn conflitantes; 0 é a checagem do estado observável no fim.")

    flag = A.churn_flag
    has_ev = pd.Series(ids.isin(c.account_id).values, index=ids)
    ended = s[s.end_date.notna()]
    has_end = pd.Series(ids.isin(ended.account_id).values, index=ids)
    assert int(flag.sum()) == cd["churn_flag"] and int(has_ev.sum()) == cd["any_churn_event"] and int(has_end.sum()) == cd["any_subscription_end"]
    assert int((flag & has_ev & has_end).sum()) == cd["all_three"]
    upset = []
    for f in (True, False):
        for e in (True, False):
            for d in (True, False):
                n = int(((flag == f) & (has_ev == e) & (has_end == d)).sum())
                upset.append({"flag": f, "event": e, "end": d, "accounts": n})

    # ---------- data quality (auditor integration, reproduced)
    tq = S["temporal"]
    rf = S["reason_feedback"]
    M("dq_usage_pre", tq[1]["share"], "52,8%", "feature_usage × subscriptions × accounts", "linha de uso",
      f"{fmt_int(tq[1]['rows_flagged'])} / {fmt_int(tq[1]['rows_total'])} linhas de uso", "Qualidade de dados / alinhamento semântico — não é causa de churn.")
    M("dq_ticket_pre", tq[3]["rows_flagged"] / tq[3]["rows_total"], "53,9%", "support_tickets × accounts", "ticket",
      f"{fmt_int(tq[3]['rows_flagged'])} / {fmt_int(tq[3]['rows_total'])} tickets", "Qualidade de dados / alinhamento semântico — não é causa de churn. Valor exato 53,85%.")
    M("dq_inlife", tq[0]["share"], "22,27%", "feature_usage × subscriptions", "linha de uso",
      f"{fmt_int(tq[0]['rows_flagged'])} / {fmt_int(tq[0]['rows_total'])} linhas de uso", "Usage coverage = 22.27% inside observed subscription lifecycle.")
    M("dq_reason_p", rf["p_chi2_452"], "p = 0,955", "churn_events.reason_code × feedback_text", "churn event",
      f"{rf['events_with_feedback']} eventos com feedback_text preenchido (3 textos distintos)",
      "Qui-quadrado, 10 g.l. (permutação p = 0,958). Nenhuma associação detectável. O 0,986 do auditor só reproduz com feedback vazio como categoria (n = 600).")

    # ---------- queues (recomputed with the validated rules, asserted against final_numbers.json)
    active = s[s.end_date.isna()]
    total = float(active.mrr_amount.sum())
    act_mrr = active.groupby("account_id").mrr_amount.sum().reindex(ids, fill_value=0)
    act_n = active.groupby("account_id").size().reindex(ids, fill_value=0)
    end_n = ended.groupby("account_id").size().reindex(ids, fill_value=0)
    ev_n = c.groupby("account_id").size().reindex(ids, fill_value=0)
    nonauto = active[~active.auto_renew_flag]
    exp_mrr = nonauto.groupby("account_id").mrr_amount.sum().reindex(ids, fill_value=0)
    exp_rec = nonauto[nonauto.mrr_amount > 0].groupby("account_id").size().reindex(ids, fill_value=0)
    nonauto_any = pd.Series(ids.isin(nonauto.account_id).values, index=ids)
    V1 = flag & (act_mrr > 0)
    vrank = act_mrr.rank(ascending=False, method="first").astype(int)
    erank = exp_mrr.rank(ascending=False, method="first").astype(int)
    V2, V3 = vrank <= 50, exp_mrr > 0
    W1 = erank <= 50
    wave1 = V1 | V2 | W1
    pilot = V3 & ~(V2 | W1)
    zero_only = nonauto_any & ~V3
    assert abs(total - N["active_mrr_proxy_total"]) < 1e-6
    assert int(V1.sum()) == N["V1"]["accounts"] and abs(act_mrr[V1].sum() - N["V1"]["active_mrr_proxy"]) < 1e-6
    assert abs(act_mrr[V2].sum() - N["V2"]["active_mrr_proxy"]) < 1e-6
    assert int(V3.sum()) == N["V3"]["accounts"] and abs(exp_mrr[V3].sum() - N["V3"]["exposed_mrr_proxy"]) < 1e-6
    assert int(W1.sum()) == N["V3W1"]["accounts"] and abs(exp_mrr[W1].sum() - N["V3W1"]["exposed_mrr_proxy"]) < 1e-6
    assert int(wave1.sum()) == N["wave1"]["union_accounts"] and int(pilot.sum()) == N["pilot"]["population"]
    assert int(zero_only.sum()) == N["V3"]["trial_only_accounts"] and int(nonauto_any.sum()) == N["V3"]["any_nonauto_accounts"]

    v1, v2, v3, w1, wv = N["V1"], N["V2"], N["V3"], N["V3W1"], N["wave1"]
    tot_s = fmt_int(total)
    M("v1_accounts", v1["accounts"], str(v1["accounts"]), "accounts.churn_flag × subscriptions", "conta", "110 / 110 contas flagged", PRIORITY_LIMIT + " Reconciliação de dados.")
    M("v1_mrr", v1["active_mrr_proxy"], fmt_int(v1["active_mrr_proxy"]), "subscriptions.mrr_amount (registros ativos)", "registro de assinatura agregado por conta", "110 contas", MRR_LIMIT)
    M("v1_share", v1["share_active"], fmt_pct(v1["share_active"]), "subscriptions.mrr_amount", "conta", f"participação no MRR proxy ativo ({tot_s})", MRR_LIMIT)
    M("v2_accounts", v2["accounts"], str(v2["accounts"]), "subscriptions.mrr_amount (registros ativos)", "conta", "top 50 de 500 contas", PRIORITY_LIMIT)
    M("v2_mrr", v2["active_mrr_proxy"], fmt_int(v2["active_mrr_proxy"]), "subscriptions.mrr_amount (registros ativos)", "registro de assinatura agregado por conta", f"50 contas / {v2['records']} registros ativos", MRR_LIMIT)
    M("v2_share", v2["share_active"], fmt_pct(v2["share_active"]), "subscriptions.mrr_amount", "conta", "participação no MRR proxy ativo", MRR_LIMIT)
    M("v3_accounts", v3["accounts"], str(v3["accounts"]), "subscriptions (ativos, auto_renew_flag=false, mrr_amount>0)", "conta", "388 contas / 764 registros", PRIORITY_LIMIT + " Não há datas de renovação nos dados.")
    M("v3_records", v3["records_with_mrr"], str(v3["records_with_mrr"]), "subscriptions (ativos, auto_renew_flag=false, mrr_amount>0)", "registro de assinatura", "764 registros em 388 contas", STATE_LIMIT)
    M("v3_mrr", v3["exposed_mrr_proxy"], fmt_int(v3["exposed_mrr_proxy"]), "subscriptions.mrr_amount (ativos, auto_renew=false)", "registro de assinatura agregado por conta", "388 contas / 764 registros", MRR_LIMIT + " Exposição de renovação manual, não estimativa de perda.")
    M("v3_share", v3["share_active"], fmt_pct(v3["share_active"]), "subscriptions.mrr_amount", "conta", "participação no MRR proxy ativo", MRR_LIMIT)
    M("v3_any_accounts", v3["any_nonauto_accounts"], str(v3["any_nonauto_accounts"]), "subscriptions (ativos, auto_renew_flag=false)", "conta", "409 contas / 899 registros",
      "Inclui exposição de trial com MRR zero. Correto só para 'qualquer registro ativo auto_renew=false, incluindo trials com MRR zero'; não é a V3 econômica.")
    M("v3_any_records", v3["any_nonauto_records"], str(v3["any_nonauto_records"]), "subscriptions (ativos, auto_renew_flag=false)", "registro de assinatura",
      "899 = 764 com MRR proxy > 0 + 135 registros de trial com MRR zero", "Inclui exposição de trial com MRR zero; não é a V3 econômica.")
    M("v3_zero_only", v3["trial_only_accounts"], str(v3["trial_only_accounts"]), "subscriptions (ativos, auto_renew_flag=false)", "conta",
      f"{v3['trial_only_accounts']} contas / {v3['trial_only_records']} registros",
      "A única exposição auto_renew=false delas é de trials com MRR zero. As 21 têm outras assinaturas pagas ativas; saem da V3 econômica, não da base de clientes.")
    M("w1_accounts", w1["accounts"], str(w1["accounts"]), "subscriptions (V3 ordenada por MRR proxy exposto)", "conta", "top 50 de 388 contas V3", PRIORITY_LIMIT + " Primeira onda operacional, não ranking de risco.")
    M("w1_records", w1["records"], str(w1["records"]), "subscriptions", "registro de assinatura", "137 registros em 50 contas", STATE_LIMIT)
    M("w1_mrr", w1["exposed_mrr_proxy"], fmt_int(w1["exposed_mrr_proxy"]), "subscriptions.mrr_amount (ativos, auto_renew=false)", "registro de assinatura agregado por conta", "50 contas / 137 registros", MRR_LIMIT)
    M("w1_share_v3", w1["share_of_V3"], fmt_pct(w1["share_of_V3"]), "subscriptions.mrr_amount", "conta", "participação na exposição V3 (2.023.778)", MRR_LIMIT)
    M("wave1", wv["union_accounts"], str(wv["union_accounts"]), "V1 ∪ V2 ∪ V3-W1", "conta", f"união, não soma (soma ingênua {wv['naive_sum']})", PRIORITY_LIMIT)
    for mid, k in [("wv_12", "V1_V2"), ("wv_1w", "V1_W1"), ("wv_2w", "V2_W1"), ("wv_all", "triple")]:
        M(mid, wv[k], str(wv[k]), "pertencimento a V1, V2, V3-W1", "conta", "176 contas únicas", PRIORITY_LIMIT)
    conc = N["concentration"]
    for k, lab in [("top10", "Top 10"), ("top20", "Top 20"), ("top50", "Top 50")]:
        M(f"conc_{k}", conc[k]["share"], fmt_pct(conc[k]["share"]), "subscriptions.mrr_amount (registros ativos)", "conta",
          f"{lab} contas: {fmt_int(conc[k]['mrr_proxy'])} de {tot_s} de MRR proxy ativo", MRR_LIMIT)
    M("total_active", total, tot_s, "subscriptions.mrr_amount (registros ativos)", "registro de assinatura agregado por conta", "500 contas / 4.514 registros ativos", MRR_LIMIT)

    # ---------- observed segment rates (auditor integration)
    seg = pd.read_csv(AUD / "segment_observed_rates_final.csv")
    seg_rows = []
    for r in seg.itertuples():
        seg_rows.append({"dimension": r.dimension, "segment": r.segment, "churned": int(r.churned), "total": int(r.total), "rate": float(r.observed_rate),
                         "ci_low": float(r.ci95_low), "ci_high": float(r.ci95_high), "eligible": bool(r.eligible_n_ge_30), "verdict": r.verdict})
    M("seg_overall", 0.22, "22,0%", "accounts.churn_flag", "conta", "110 / 500 contas", "Taxa observada de um dos três sinais de churn, que discordam entre si.")
    for r in seg[seg.eligible_n_ge_30].head(5).itertuples():
        M(f"seg_{r.segment}", float(r.observed_rate), fmt_pct(r.observed_rate), "accounts.churn_flag", "conta",
          f"{r.churned} / {r.total} contas; IC 95% de Wilson {fmt_pct(r.ci95_low)}–{fmt_pct(r.ci95_high)}",
          "Observed — not validated as higher risk. Nenhuma dimensão atinge p < 0,05 (menor q = 0,28).")

    # ---------- usage over time (same rule as end_to_end_sweep / final_rewrite_build)
    us = u.merge(s[["subscription_id", "account_id"]]).merge(a[["account_id", "industry", "country", "plan_tier"]])
    quarters = pd.period_range("2023Q1", "2024Q4", freq="Q")

    def series(acc_ids):
        ss = s[s.account_id.isin(acc_ids)]
        uu = us[us.account_id.isin(acc_ids)]
        out = []
        for q in quarters:
            lo, hi = q.start_time, q.end_time.normalize()
            act = ss[(ss.start_date <= hi) & (ss.end_date.isna() | (ss.end_date > hi))]
            tot = int(uu[(uu.usage_date >= lo) & (uu.usage_date <= hi)].usage_count.sum())
            na, nsub = int(act.account_id.nunique()), len(act)
            out.append({"quarter": str(q), "usage_total": tot, "active_accounts": na, "active_subscriptions": nsub,
                        "per_active_account": tot / na if na else None, "per_active_subscription": tot / nsub if nsub else None})
        return out

    usage = {"ALL": series(ids)}
    qc = pd.read_csv(SWEEP / "quarterly_claims.csv").set_index("quarter")
    for row in usage["ALL"]:
        ref = qc.loc[row["quarter"]]
        assert row["usage_total"] == int(ref.usage_total) and abs(row["per_active_account"] - ref.usage_per_active_account) < 1e-9
        assert abs(row["per_active_subscription"] - ref.usage_per_active_subscription) < 1e-9
    for dim in ["industry", "country", "plan_tier"]:
        for lvl in sorted(a[dim].unique()):
            usage[f"{dim}:{lvl}"] = series(a[a[dim] == lvl].account_id)
    seg_usage = pd.read_csv(FINAL / "segment_usage_per_active_account.csv").to_dict("records")
    M("usage_chart", None, "Uso ao longo do tempo", "feature_usage × subscriptions × accounts", "trimestre",
      "25.000 linhas de uso; 500 contas; 5.000 registros de assinatura", DENOM_PT + " " + NUMER_PT)

    # ---------- subscription semantics
    sem = S["subscription_semantics"]
    M("sub_flag", sem["subscriptions_churn_flag_true"], str(sem["subscriptions_churn_flag_true"]), "subscriptions.churn_flag", "registro de assinatura", "5.000 registros",
      "Exatamente os mesmos 486 registros têm end_date; nenhum churn_flag = false tem end_date. Não é um novo target independente.")
    M("sub_end", sem["subscriptions_with_end_date"], str(sem["subscriptions_with_end_date"]), "subscriptions.end_date", "registro de assinatura", "5.000 registros", "Representação duplicada do fim de assinatura.")
    M("sub_per_acc", sem["mean_active_records_per_account"], f"{sem['mean_active_records_per_account']:.1f}".replace(".", ","), "subscriptions (ativos em 31/12/2024)", "conta",
      f"{fmt_int(sem['active_records'])} registros ativos / 500 contas", "The schema does not establish that each subscription record maps one-to-one to a commercial contract.")
    M("sub_all3", sem["accounts_all_three_plans_active"], f"{sem['accounts_all_three_plans_active']} / 500", "subscriptions.plan_tier (ativos)", "conta", "500 contas",
      "The schema does not establish that each subscription record maps one-to-one to a commercial contract.")

    # ---------- impact lab (pre-computed lookup 0..20%)
    exposure = N["V3"]["exposed_mrr_proxy"]
    impact = [{"pct": p, "monthly": exposure * p / 100, "annualized": exposure * p / 100 * 12} for p in range(0, 21)]
    for sc in N["scenarios_on_V3"]:
        row = impact[round(sc["pct"] * 100)]
        assert abs(row["monthly"] - sc["mrr_proxy"]) < 1e-6 and abs(row["annualized"] - sc["annualized_proxy"]) < 1e-6
    M("impact_base", exposure, fmt_int(exposure), "subscriptions.mrr_amount (V3)", "registro de assinatura agregado por conta", "388 contas / 764 registros",
      "Scenario — not forecast. Sem probabilidade. Sem estimativa causal. " + MRR_LIMIT)
    pl = N["pilot"]
    M("pilot_pop", pl["population"], str(pl["population"]), "V3 − V2 − V3-W1", "conta", f"{pl['population']} contas; {fmt_int(pl['exposed_mrr_proxy'])} de MRR proxy exposto",
      "Exclui contas já cobertas pela V2 ou contatadas na V3-W1 (contaminação).")
    M("pilot_arm", pl["per_arm"], f"{pl['per_arm']} / {pl['per_arm']}", "desenho do piloto", "conta", "sorteio por conta antes de qualquer contato com o cliente", "Só desenho — não lançado.")
    for b, v in pl["mde_pp"].items():
        M(f"mde_{b}", v, f"~{v:.1f} pp".replace(".", ","), "statsmodels NormalIndPower (bicaudal, alfa 0,05, poder 80%)", "conta", f"{pl['per_arm']} por braço",
          "Premissas hipotéticas de taxa base — não são dados observados.")

    hs = N["health_score_readiness"]
    M("health", hs, f"{hs['green']} GREEN · {hs['partial']} PARTIAL · {hs['red']} RED", "checklist A5 do TECHNICAL-APPENDIX", "item de prontidão", "10 itens",
      "Não construir health score agora.")

    # ---------- per-account brief
    uu = u.merge(s[["subscription_id", "account_id", "start_date", "end_date"]]).merge(a[["account_id", "signup_date"]])
    uu["in_life"] = (uu.usage_date >= uu.start_date) & (uu.end_date.isna() | (uu.usage_date <= uu.end_date))
    ua = uu.groupby("account_id").agg(usage_rows=("usage_id", "size"), usage_count=("usage_count", "sum"), features=("feature_name", "nunique"),
                                      errors=("error_count", "sum"), in_life_share=("in_life", "mean"))
    ta = t.groupby("account_id").agg(tickets=("ticket_id", "size"), escalations=("escalation_flag", "sum"), frt=("first_response_time_minutes", "mean"),
                                     resolution=("resolution_time_hours", "mean"), csat=("satisfaction_score", "mean"),
                                     csat_missing=("satisfaction_score", lambda x: int(x.isna().sum())))
    flags = pd.read_csv(AUD / "account_data_quality_flags.csv").set_index("account_id")
    for k, n in S["account_flag_counts"].items():
        assert int(flags[k].sum()) == n

    def band(r):
        return "Top 10" if r <= 10 else "Posição 11–50" if r <= 50 else "Posição 51–150" if r <= 150 else "Posição 151–500"

    accounts = []
    for aid in ids:
        r = A.loc[aid]
        subs = s[s.account_id == aid].sort_values("start_date")
        evs = c[c.account_id == aid].sort_values("churn_date")
        q = [k for k, m in [("V1", V1), ("V2", V2), ("V3", V3), ("V3-W1", W1)] if m[aid]]
        ar = active[active.account_id == aid]
        accounts.append({
            "id": aid, "name": r.account_name, "industry": r.industry, "country": r.country, "channel": r.referral_source, "plan": r.plan_tier,
            "signup": r.signup_date.date().isoformat(), "churn_flag": bool(r.churn_flag),
            "queues": q, "wave1": bool(wave1[aid]), "pilot": bool(pilot[aid]), "zero_only": bool(zero_only[aid]),
            "active_mrr": float(act_mrr[aid]), "value_rank": int(vrank[aid]), "value_band": band(int(vrank[aid])),
            "exposed_mrr": float(exp_mrr[aid]), "exposed_records": int(exp_rec[aid]), "exposure_rank": int(erank[aid]) if exp_mrr[aid] > 0 else None,
            "active_records": int(act_n[aid]), "ended_records": int(end_n[aid]), "churn_events": int(ev_n[aid]),
            "auto_renew_active": {"on": int(ar.auto_renew_flag.sum()), "off": int((~ar.auto_renew_flag).sum())},
            "plans_active": sorted(ar.plan_tier.unique().tolist()),
            "subscriptions": [{"id": x.subscription_id, "plan": x.plan_tier, "start": x.start_date.date().isoformat(),
                               "end": x.end_date.date().isoformat() if pd.notna(x.end_date) else None, "mrr": float(x.mrr_amount),
                               "trial": bool(x.is_trial), "auto_renew": bool(x.auto_renew_flag), "billing": x.billing_frequency} for x in subs.itertuples()],
            "events": [{"date": e.churn_date.date().isoformat(), "reason": e.reason_code, "feedback": e.feedback_text if pd.notna(e.feedback_text) else None,
                        "reactivation": bool(e.is_reactivation)} for e in evs.itertuples()],
            "usage": {k: (None if aid not in ua.index else (float(ua.loc[aid, k]) if k == "in_life_share" else int(ua.loc[aid, k])))
                      for k in ["usage_rows", "usage_count", "features", "errors", "in_life_share"]},
            "support": {"tickets": int(ta.loc[aid, "tickets"]) if aid in ta.index else 0,
                        "escalations": int(ta.loc[aid, "escalations"]) if aid in ta.index else 0,
                        "frt": float(ta.loc[aid, "frt"]) if aid in ta.index else None,
                        "resolution": float(ta.loc[aid, "resolution"]) if aid in ta.index else None,
                        "csat": float(ta.loc[aid, "csat"]) if aid in ta.index and pd.notna(ta.loc[aid, "csat"]) else None,
                        "csat_missing": int(ta.loc[aid, "csat_missing"]) if aid in ta.index else 0},
            "flags": {k: bool(flags.loc[aid, k]) for k in flags.columns},
        })
    assert sum(1 for x in accounts if "V3" in x["queues"]) == 388 and sum(1 for x in accounts if x["wave1"]) == 176

    # ---------- metadata for charts, tables and brief sections (no single number)
    M("upset", None, "Sobreposição dos três sinais de churn", "accounts.churn_flag, churn_events, subscriptions.end_date", "conta", "500 contas",
      "Interseções exclusivas: cada conta é contada uma vez, na combinação a que pertence.")
    M("seg_change", None, "Uso por conta ativa, 2023H2 → 2024H2", "feature_usage × subscriptions × accounts", "segmento (atributo da conta)", "15 segmentos",
      DENOM_PT + " A direção se mantém; o percentual depende desse denominador.")
    M("seg_forest", None, "Taxa observada de churn_flag por segmento", "accounts.churn_flag", "conta", "segmentos com N ≥ 30 (regra pré-definida)",
      "Observed — not validated as higher risk. IC 95% de Wilson. Nenhuma dimensão atinge p < 0,05 (menor q = 0,28).")
    M("queue_table", None, "Contas das filas", "subscriptions, accounts, churn_events", "conta", "contas em V1 ∪ V2 ∪ V3", PRIORITY_LIMIT + " " + MRR_LIMIT)
    M("brief_value", None, "Valor", "subscriptions.mrr_amount", "registro de assinatura agregado por conta", "registros desta conta", MRR_LIMIT)
    M("brief_lifecycle", None, "Lifecycle", "subscriptions, churn_events", "registro de assinatura / evento", "registros desta conta",
      STATE_LIMIT + " Não existem renewal date, contract_id nem product_id nos dados.")
    M("brief_product", None, "Produto", "feature_usage × subscriptions", "linha de uso", "linhas de uso desta conta",
      "Usage coverage = 22.27% inside observed subscription lifecycle (todas as contas). A cobertura abaixo é a parcela das linhas desta conta dentro do lifecycle.")
    M("brief_support", None, "Suporte", "support_tickets", "ticket", "tickets desta conta",
      "53,9% de todos os tickets são anteriores ao signup da conta. CSAT observado só na escala 3–5; 41,25% sem resposta no total.")
    M("brief_dq", None, "Flags de qualidade de dados", "auditor_integration/account_data_quality_flags.csv", "conta", "500 contas",
      "Flags descritivas sim/não. Nunca somadas, ponderadas ou ordenadas — não é score.")
    M("impact_slider", None, "MRR proxy condicional", "exposição V3 × percentual escolhido (pré-calculado 0–20%)", "cenário", "388 contas / 764 registros",
      "Scenario — not forecast. Sem probabilidade. Sem estimativa causal.")
    M("break_even", None, "Percentual de break-even", "custo hipotético informado pelo usuário ÷ 2.023.778", "cenário", "exposição V3",
      "Custo hipotético informado pelo usuário. Não é recomendação nem previsão.")

    confidence = [
        {"dimension": "Definição do outcome", "status": "RED", "detail": "110 / 352 / 312 = três populações de churn conflitantes. 0 = checagem do estado observável no fim.", "metric": "conf_outcome"},
        {"dimension": "Semântica das assinaturas", "status": "RED", "detail": "9,0 registros ativos por conta; 418 / 500 com Basic, Pro e Enterprise ativos", "metric": "sub_per_acc"},
        {"dimension": "Datas de renovação", "status": "RED", "detail": "Campo inexistente", "metric": None},
        {"dimension": "Contract ID", "status": "RED", "detail": "Campo inexistente", "metric": None},
        {"dimension": "Product ID", "status": "RED", "detail": "Campo inexistente", "metric": None},
        {"dimension": "Alinhamento do uso ao lifecycle", "status": "PARTIAL", "detail": "22,27% das linhas de uso dentro da vida observada da assinatura", "metric": "dq_inlife"},
        {"dimension": "Uso antes do signup", "status": "WARNING", "detail": "52,8% das linhas de uso são anteriores ao signup da conta", "metric": "dq_usage_pre"},
        {"dimension": "Suporte antes do signup", "status": "WARNING", "detail": "53,9% dos tickets são anteriores ao signup da conta", "metric": "dq_ticket_pre"},
        {"dimension": "Coerência semântica do reason code", "status": "RED", "detail": "p = 0,955 contra o feedback_text preenchido", "metric": "dq_reason_p"},
        {"dimension": "Histórico financeiro", "status": "PARTIAL", "detail": "MRR proxy por registro, reconstruível mas não consolidado", "metric": "total_active"},
    ]
    health_items = [("Objetivo único", "RED"), ("Alvo rotulado", "RED"), ("Eventos de renovação", "RED"), ("Janela ≥ 1 ciclo", "RED"),
                    ("Uso ligado ao lifecycle", "PARTIAL"), ("Timing de suporte coerente", "RED"), ("Histórico financeiro", "PARTIAL"),
                    ("Sinais de relacionamento", "RED"), ("Validação fora da amostra acima do baseline", "RED"), ("Playbook com dono", "RED")]
    assert sum(1 for _, st in health_items if st == "RED") == hs["red"] and sum(1 for _, st in health_items if st == "PARTIAL") == hs["partial"]

    data = {
        "generated_from": ["solution/outputs/final_rewrite/final_numbers.json", "solution/outputs/auditor_integration/auditor_integration_summary.json",
                           "solution/outputs/auditor_integration/*.csv", "solution/outputs/end_to_end_sweep/quarterly_claims.csv", "dados/raw/ravenstack/*.csv"],
        "metrics": metrics, "upset": upset, "segments": seg_rows, "segment_usage_change": seg_usage,
        "usage": usage, "usage_definition": {**den, "active_account_rule_pt": DENOM_PT, "numerator_note_pt": NUMER_PT},
        "impact": impact, "accounts": accounts,
        "confidence": confidence, "health_items": [{"item": i, "status": st} for i, st in health_items],
        "concentration": {k: N["concentration"][k] for k in N["concentration"]},
    }
    LAB.mkdir(parents=True, exist_ok=True)
    js = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    (LAB / "truth_lab_data.json").write_text(js, encoding="utf-8")
    (LAB / "truth_lab_data.js").write_text("window.TRUTH_LAB_DATA=" + js + ";\n", encoding="utf-8")
    print(f"metrics: {len(metrics)}  accounts: {len(accounts)}  usage series: {len(usage)}  json: {len(js) / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
