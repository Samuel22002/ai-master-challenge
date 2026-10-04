"""TRUTH-LAB-BUILD-02 — automated acceptance checks for the static Churn Truth Lab.

1. Numeric tests: truth_lab_data.json against the validated outputs (final_numbers.json,
   auditor_integration_summary.json) and the literal values required by the build prompt.
2. Forbidden-phrase and currency scan over every shipped file (html, css, js, json, md).
   The only exception is the mandatory negated label "Business priority — not predicted churn risk".
3. Offline scan: no http(s) URL, protocol-relative URL, @import or CDN reference in any shipped
   file (the SVG XML namespace string is not a request and is allow-listed).
4. File tree.
5. Functional tests: runs index.html?selftest=1 in headless Edge/Chrome from file:// and parses
   the in-page self-test results (views, filters, search, sort, brief, CSV, simulator, metadata,
   window/console errors).

Exit code 1 on any failure.
Run: python solution/scripts/check_truth_lab.py
"""
from __future__ import annotations

import html
import shutil
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from _paths import OUTPUTS, PKG, RAW_DIR, ROOT  # noqa: E402,F401  (package paths)
LAB = PKG / "solution" / "truth-lab"
OUT = OUTPUTS / "truth_lab"
N = json.loads((OUTPUTS / "final_rewrite" / "final_numbers.json").read_text(encoding="utf-8"))
S = json.loads((OUTPUTS / "auditor_integration" / "auditor_integration_summary.json").read_text(encoding="utf-8"))

FORBIDDEN = ["high churn risk", "predicted churn risk", "predicted risk", "churn probability", "likelihood to churn", "likely to churn",
             "revenue at risk", "expected loss", "expected savings", "still paying", "real churn = 0", "zero customers churned", "risk score",
             # Portuguese equivalents (UI is in Portuguese since FINAL-CLOSEOUT-TRUTH-LAB-01)
             "continuam pagando", "continua pagando", "probabilidade de churn", "receita em risco", "alto risco", "risco previsto",
             "perda esperada", "economia esperada", "receita",
             # superseded wording (FINAL-CLOSEOUT-TRUTH-LAB-01 items 1, 12, 13)
             "four definitions", "quatro definições", "unsafe", "at stake"]
ALLOWED = ["business priority — not predicted churn risk"]
CURRENCY = re.compile(r"R\$|US\$|\bBRL\b|\bUSD\b|\$\s?\d|\d\s?\$")
EXTERNAL = re.compile(r"https?://|(?:src|href)\s*=\s*[\"']//|@import|cdn\.|googleapis|cdnjs|jsdelivr|unpkg")
NS_OK = "http://www.w3.org/2000/svg"
BROWSERS = [Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"), Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")] + [
            Path(w) for w in (shutil.which(n) for n in ("msedge", "microsoft-edge", "google-chrome", "chromium", "chromium-browser", "chrome")) if w]

results: list[dict] = []


def check(group: str, name: str, cond: bool, detail="") -> None:
    results.append({"group": group, "test": name, "status": "PASS" if cond else "FAIL", "detail": str(detail)})


def numeric(D: dict) -> None:
    M = D["metrics"]
    v = lambda k: M[k]["value"]
    cd = N["churn_definitions"]
    for k, exp in [("def_flag", 110), ("def_event", 352), ("def_end", 312), ("def_zero", 0), ("ov_fe", 75), ("ov_fn", 72), ("ov_en", 227), ("ov_all", 50)]:
        check("numeric", f"{k} = {exp}", v(k) == exp and exp in cd.values(), v(k))
    for k, exp in [("v1_accounts", 110), ("v2_accounts", 50), ("v3_accounts", 388), ("w1_accounts", 50), ("wave1", 176), ("v3_records", 764), ("w1_records", 137),
                   ("wv_12", 9), ("wv_1w", 11), ("wv_2w", 17), ("wv_all", 3), ("v3_any_accounts", 409), ("v3_any_records", 899), ("v3_zero_only", 21),
                   ("pilot_pop", 314), ("sub_flag", 486), ("sub_end", 486)]:
        check("numeric", f"{k} = {exp}", v(k) == exp, v(k))
    for k, exp in [("v1_mrr", 2073153), ("v2_mrr", 2781650), ("v3_mrr", 2023778), ("w1_mrr", 873996), ("impact_base", 2023778)]:
        check("numeric", f"{k} = {exp:,}", round(v(k)) == exp and M[k]["display"] == f"{exp:,}".replace(",", "."), M[k]["display"])
    for k, exp in [("v1_share", "20,4%"), ("v2_share", "27,4%"), ("v3_share", "19,9%"), ("w1_share_v3", "43,2%"), ("conc_top10", "8,4%"), ("conc_top20", "14,3%"),
                   ("conc_top50", "27,4%"), ("dq_usage_pre", "52,8%"), ("dq_ticket_pre", "53,9%"), ("dq_inlife", "22,27%"), ("dq_reason_p", "p = 0,955"),
                   ("seg_overall", "22,0%"), ("pilot_arm", "157 / 157"), ("sub_all3", "418 / 500"), ("sub_per_acc", "9,0"),
                   ("mde_0.1", "~7,4 pp"), ("mde_0.15", "~9,4 pp"), ("mde_0.2", "~11,0 pp"), ("health", "0 GREEN · 2 PARTIAL · 8 RED")]:
        check("numeric", f"{k} displays {exp}", M[k]["display"] == exp, M[k]["display"])
    t = S["temporal"]
    check("numeric", "usage inside lifecycle 5,568 / 25,000", t[0]["rows_flagged"] == 5568 and t[0]["rows_total"] == 25000)
    check("numeric", "usage before signup 13,198 / 25,000", t[1]["rows_flagged"] == 13198 and t[1]["rows_total"] == 25000)
    check("numeric", "tickets before signup 1,077 / 2,000", t[3]["rows_flagged"] == 1077 and t[3]["rows_total"] == 2000)
    check("numeric", "452 populated feedback events", S["reason_feedback"]["events_with_feedback"] == 452)
    check("numeric", "reason × feedback p = 0.955", round(S["reason_feedback"]["p_chi2_452"], 3) == 0.955, S["reason_feedback"]["p_chi2_452"])
    check("numeric", "486 churn flags = 486 end dates", S["subscription_semantics"]["churn_flag_equals_end_date_all_rows"])
    check("numeric", "418 / 500 all-three-plan accounts", S["subscription_semantics"]["accounts_all_three_plans_active"] == 418)
    for p, mo, an in [(5, 101189, 1214267), (10, 202378, 2428534), (15, 303567, 3642800)]:
        r = D["impact"][p]
        check("numeric", f"impact {p}% = {mo:,} / {an:,}", round(r["monthly"]) == mo and round(r["annualized"]) == an, (round(r["monthly"]), round(r["annualized"])))
    check("numeric", "health items 0 GREEN / 2 PARTIAL / 8 RED", [i["status"] for i in D["health_items"]].count("RED") == 8 and
          [i["status"] for i in D["health_items"]].count("PARTIAL") == 2 and [i["status"] for i in D["health_items"]].count("GREEN") == 0)
    acc = D["accounts"]
    check("numeric", "500 accounts in brief data", len(acc) == 500)
    for q, exp in [("V1", 110), ("V2", 50), ("V3", 388), ("V3-W1", 50)]:
        check("numeric", f"accounts tagged {q} = {exp}", sum(q in a["queues"] for a in acc) == exp)
    check("numeric", "first wave tagged = 176", sum(a["wave1"] for a in acc) == 176)
    check("numeric", "pilot tagged = 314", sum(a["pilot"] for a in acc) == 314)
    check("numeric", "zero-value non-auto-renew only = 21", sum(a["zero_only"] for a in acc) == 21)
    check("numeric", "sum of V1 active MRR proxy = 2,073,153", round(sum(a["active_mrr"] for a in acc if "V1" in a["queues"])) == 2073153)
    check("numeric", "sum of V3 exposed MRR proxy = 2,023,778", round(sum(a["exposed_mrr"] for a in acc if "V3" in a["queues"])) == 2023778)
    seg = {r["segment"]: r for r in D["segments"]}
    for sg, k, n in [("DevTools", 35, 113), ("event", 29, 96), ("2023H1", 29, 109), ("True", 25, 97), ("6-15", 33, 134)]:
        check("numeric", f"segment {sg} {k} / {n} (N ≥ 30)", seg[sg]["churned"] == k and seg[sg]["total"] == n and seg[sg]["eligible"])
    check("numeric", "Germany 8 / 25 excluded (N < 30)", seg["DE"]["churned"] == 8 and seg["DE"]["total"] == 25 and not seg["DE"]["eligible"])
    q = D["usage"]["ALL"]
    check("numeric", "usage quarterly total range 30,789–32,227", min(r["usage_total"] for r in q) == N["usage"]["quarterly_total_min"] and max(r["usage_total"] for r in q) == N["usage"]["quarterly_total_max"])
    check("numeric", "usage denominator rule embedded", "period-end date" in D["usage_definition"]["active_account_rule"])
    for k, x in M.items():
        if not all(str(x.get(f) or "").strip() for f in ["source", "grain", "coverage", "limitation"]):
            check("metadata", f"{k} has SOURCE/GRAIN/COVERAGE/LIMITATION", False)
    check("metadata", f"all {len(M)} metrics have SOURCE/GRAIN/COVERAGE/LIMITATION",
          all(all(str(x.get(f) or "").strip() for f in ["source", "grain", "coverage", "limitation"]) for x in M.values()))


def shipped_files() -> list[Path]:
    return [p for p in LAB.rglob("*") if p.is_file() and p.suffix in {".html", ".css", ".js", ".json", ".md"}]


def scans() -> None:
    for p in shipped_files():
        rel = p.relative_to(LAB).as_posix()
        text = p.read_text(encoding="utf-8")
        low = text.lower()
        for a in ALLOWED:
            low = low.replace(a, " ")
        if rel == "assets/js/app.js":
            # the in-page self-test lists the forbidden phrases it searches for
            low = re.sub(r"const forbidden = \[.*?\];", "", low, flags=re.S)
            low = re.sub(r"function forbiddenhits\(text\) \{.*?\n  \}", "", low, flags=re.S)  # the scanner's own code
        if rel == "README.md":
            low = re.sub(r"<!-- forbidden-list -->.*?<!-- /forbidden-list -->", "", low, flags=re.S)
        hits = [f for f in FORBIDDEN if f in low]
        check("forbidden", f"no forbidden phrase in {rel}", not hits, ",".join(hits))
        # 'revenue' may appear only in the mandatory label "MRR proxy — not consolidated revenue"
        rev = [m.start() for m in re.finditer(r"revenue", low) if "consolidated revenue" not in low[max(0, m.start() - 14): m.end()]]
        check("forbidden", f"'revenue' only in the mandatory label in {rel}", not rev, len(rev))
        body = text
        if p.suffix == ".js":
            body = body.replace("${", "")  # JS template-literal syntax, not a currency sign
            body = "\n".join(ln for ln in body.splitlines() if "forbiddenHits" not in ln and "(r\\$|us\\$" not in ln)  # the self-test's own currency regex
        if rel == "README.md":
            body = re.sub(r"<!-- forbidden-list -->.*?<!-- /forbidden-list -->", "", body, flags=re.S)
        cur = CURRENCY.findall(body)
        check("currency", f"no currency symbol/code in {rel}", not cur, cur[:5])
        ext = [m.group(0) for m in EXTERNAL.finditer(text.replace(NS_OK, ""))]
        if rel == "README.md":
            ext = []  # documentation, not loaded by the page
        check("offline", f"no external reference in {rel}", not ext, ext[:5])


def tree() -> None:
    for rel in ["index.html", "assets/css/app.css", "assets/js/app.js", "data/truth_lab_data.json", "data/truth_lab_data.js", "README.md"]:
        check("files", f"{rel} exists", (LAB / rel).is_file())
    idx = (LAB / "index.html").read_text(encoding="utf-8")
    check("files", "index.html loads only relative local assets", all(not s.startswith(("http", "//")) for s in re.findall(r'(?:src|href)="([^"]+)"', idx) if not s.startswith("#")))
    j = json.loads((LAB / "data" / "truth_lab_data.json").read_text(encoding="utf-8"))
    js = (LAB / "data" / "truth_lab_data.js").read_text(encoding="utf-8")
    check("files", "data .js wrapper equals .json", json.loads(js[len("window.TRUTH_LAB_DATA="):].rstrip().rstrip(";")) == j)


def functional() -> None:
    exe = next((b for b in BROWSERS if b.exists()), None)
    if not exe:
        check("functional", "headless browser available", False, "Edge/Chrome not found")
        return
    url = (LAB / "index.html").resolve().as_uri() + "?selftest=1"
    with tempfile.TemporaryDirectory() as prof:
        # network disabled: every hostname unresolvable and all traffic sent to a dead proxy — the page must still pass
        out = subprocess.run([str(exe), "--headless=new", "--disable-gpu", "--no-first-run", f"--user-data-dir={prof}", "--virtual-time-budget=15000",
                              "--host-resolver-rules=MAP * ~NOTFOUND", "--proxy-server=127.0.0.1:9", "--dump-dom", url], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180).stdout
    m = re.search(r'<pre id="selftest-results"[^>]*>(.*?)</pre>', out, re.S)
    if not m:
        check("functional", "self-test ran in headless browser", False, "no results in DOM")
        return
    lines = html.unescape(m.group(1)).splitlines()
    check("functional", f"self-test header: {lines[0]}", lines[0].startswith("SELFTEST PASS"), lines[0])
    for ln in lines[1:]:
        st, _, rest = ln.partition(" | ")
        name, _, det = rest.partition(" | ")
        check("functional", name, st == "PASS", det)
    (OUT / "selftest_dom_results.txt").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    D = json.loads((LAB / "data" / "truth_lab_data.json").read_text(encoding="utf-8"))
    numeric(D); scans(); tree(); functional()
    import csv
    with (OUT / "truth_lab_checks.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["group", "test", "status", "detail"]); w.writeheader(); w.writerows(results)
    groups = {}
    for r in results:
        g = groups.setdefault(r["group"], [0, 0]); g[0 if r["status"] == "PASS" else 1] += 1
    for g, (p, f) in groups.items():
        print(f"{g:11s} PASS {p:3d}  FAIL {f}")
    fails = [r for r in results if r["status"] == "FAIL"]
    for r in fails:
        print("FAIL", r["group"], r["test"], r["detail"])
    print("TOTAL", len(results) - len(fails), "/", len(results))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
