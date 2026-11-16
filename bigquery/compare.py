"""Compare the BigQuery path (bigquery/*.sql + BigQuery ML) with the DuckDB/numpy path.

Reads results/variance_reduction.json and results/bigquery_*.json, recomputes lift,
standard errors and variance reduction from the BigQuery per-arm aggregates, and
fails on any mismatch beyond tolerance. Writes results/bigquery_comparison.json.

Tolerances: row counts and raw rates must match exactly (same data, same SQL
aggregates). The adjusted figures depend on two independent OLS fits (numpy vs
BigQuery ML), so they are compared at 1e-6 absolute on lifts and 1e-3 relative on
standard errors. Deciles depend on where each engine places ties at the cut points,
so per-decile counts are compared at 0.5% and per-decile lifts at 0.05 pp.
"""
import json
import math
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1] / "results"
Z = 1.959963984540054


def load(name):
    return json.loads((R / name).read_text())


def num(x):
    return float(x) if x is not None else None


ref = load("variance_reduction.json")
checks, failures = [], []


def check(name, a, b, tol, rel=False):
    diff = abs(a - b) / (abs(b) if rel and b else 1)
    ok = diff <= tol
    checks.append({"check": name, "duckdb": b, "bigquery": a, "diff": diff, "tol": tol, "ok": ok})
    if not ok:
        failures.append(name)


n_bq = int(load("bigquery_rowcount.json")[0]["n"])
check("rows", n_bq, ref["rows"], 0)

for y in ["visit", "conversion"]:
    r = ref[y]
    arms = {int(a["treatment"]): a for a in load(f"bigquery_cuped_{y}.json")}
    t, c = arms[1], arms[0]
    n1, n0 = int(t["n"]), int(c["n"])
    check(f"{y} n_treated", n1, r["n_treated"], 0)
    check(f"{y} n_control", n0, r["n_control"], 0)
    check(f"{y} rate_treated", num(t["mean_y"]), r["rate_treated"], 1e-12)
    check(f"{y} rate_control", num(c["mean_y"]), r["rate_control"], 1e-12)
    raw_se = math.sqrt(num(t["var_y"]) / n1 + num(c["var_y"]) / n0)
    adj_lift = num(t["mean_ystar"]) - num(c["mean_ystar"])
    adj_se = math.sqrt(num(t["var_ystar"]) / n1 + num(c["var_ystar"]) / n0)
    check(f"{y} raw se", raw_se, r["raw"]["se"], 1e-9, rel=True)
    check(f"{y} cuped lift", adj_lift, r["cuped"]["abs_lift"], 1e-6)
    check(f"{y} cuped se", adj_se, r["cuped"]["se"], 1e-3, rel=True)
    check(f"{y} variance reduction", 1 - (adj_se / raw_se) ** 2, r["variance_reduction"], 1e-3)

    seg = {}
    for row in load(f"bigquery_segments_{y}.json"):
        seg.setdefault(int(row["decile"]), {})[int(row["treatment"])] = row
    for s in r["segments"]:
        d = seg[s["decile"]]
        n1d, n0d = int(d[1]["n"]), int(d[0]["n"])
        lift = num(d[1]["mean_y"]) - num(d[0]["mean_y"])
        check(f"{y} decile {s['decile']} n", n1d + n0d, s["n_treated"] + s["n_control"], 5e-3, rel=True)
        check(f"{y} decile {s['decile']} lift", lift, s["abs_lift"], 5e-4)

out = {"passed": not failures, "n_checks": len(checks), "failures": failures, "checks": checks}
(R / "bigquery_comparison.json").write_text(json.dumps(out, indent=2))
print(f"{len(checks) - len(failures)}/{len(checks)} checks match")
for f in failures:
    print("MISMATCH:", f)
sys.exit(1 if failures else 0)
