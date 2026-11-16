"""CUPED-style variance reduction and decile segment effects on the full Criteo release.

Reference path (DuckDB + numpy). An independent BigQuery path lives in bigquery/;
bigquery/compare.py checks the two against each other.

Input: the official criteo-research-uplift-v2.1.csv.gz (13,979,592 rows;
f0..f11 are pre-treatment user features, then treatment, conversion, visit, exposure).

Method, per outcome Y in {visit, conversion}:
  1. Regress Y on f0..f11 (pooled over both arms, no treatment term) using
     population covariances computed in SQL; solve the 12x12 system in numpy.
  2. Covariate C = fitted value (centered). Treatment is randomized and the
     features are pre-treatment, so adjusting by C leaves the effect unbiased
     and removes the variance the features explain (regression-adjusted CUPED,
     also called CUPAC when the covariate is a model prediction).
  3. theta = cov(Y, C) / var(C); Y* = Y - theta * (C - mean(C)).
  4. Report raw vs adjusted lift, standard errors, variance reduction and the
     equivalent sample-size saving.
  5. Segments: deciles of C (predicted baseline propensity). Per-decile lift,
     95% CI, and Cochran's Q test for heterogeneity across deciles.

Also checks covariate balance (standardized mean differences) between arms,
which is what makes the pre-treatment assumption testable.

Usage: python variance_reduction/cuped_segments.py <criteo csv.gz> [--out results/variance_reduction.json]
"""
import argparse
import json
from pathlib import Path

import duckdb
import numpy as np
from scipy.stats import chi2, norm

FEATURES = [f"f{i}" for i in range(12)]
OUTCOMES = ["visit", "conversion"]
EXPECTED_ROWS = 13_979_592
Z = norm.ppf(0.975)


def fit_slopes(con, y, feats):
    """OLS slopes from population covariances (intercept not needed for centered adjustment)."""
    pairs = [(a, b) for i, a in enumerate(feats) for b in feats[i:]]
    sel = [f"covar_pop({a},{b}) AS c_{a}_{b}" for a, b in pairs]
    sel += [f"covar_pop({a},{y}) AS cy_{a}" for a in feats]
    row = con.execute(f"SELECT {', '.join(sel)} FROM t").fetchone()
    k = len(feats)
    sxx = np.zeros((k, k))
    idx = {f: i for i, f in enumerate(feats)}
    for (a, b), v in zip(pairs, row[: len(pairs)]):
        sxx[idx[a], idx[b]] = sxx[idx[b], idx[a]] = v
    sxy = np.array(row[len(pairs):])
    return np.linalg.solve(sxx, sxy)


def two_arm(n1, m1, v1, n0, m0, v0):
    lift = m1 - m0
    se = float(np.sqrt(v1 / n1 + v0 / n0))
    return lift, se


def analyse(con, y, feats):
    beta = fit_slopes(con, y, feats)
    means = con.execute(f"SELECT {', '.join(f'avg({f})' for f in feats)} FROM t").fetchone()
    expr = " + ".join(f"({float(b)!r})*({f} - ({float(m)!r}))" for b, f, m in zip(beta, feats, means))
    con.execute(f"CREATE OR REPLACE TEMP TABLE s AS SELECT treatment, {y} AS y, {expr} AS c FROM t")
    theta = con.execute("SELECT covar_pop(y, c) / var_pop(c) FROM s").fetchone()[0]
    con.execute(f"CREATE OR REPLACE TEMP TABLE a AS SELECT treatment, y, c, y - {float(theta)!r} * c AS ystar FROM s")
    arms = {r[0]: r[1:] for r in con.execute(
        "SELECT treatment, count(*), avg(y), var_samp(y), avg(ystar), var_samp(ystar) FROM a GROUP BY 1").fetchall()}
    n1, my1, vy1, ms1, vs1 = arms[1]
    n0, my0, vy0, ms0, vs0 = arms[0]
    raw_lift, raw_se = two_arm(n1, my1, vy1, n0, my0, vy0)
    adj_lift, adj_se = two_arm(n1, ms1, vs1, n0, ms0, vs0)
    var_red = 1 - (adj_se / raw_se) ** 2

    # deciles of the covariate (predicted baseline); ties broken by row order of the scan
    seg = con.execute("""
        WITH d AS (SELECT treatment, y, ntile(10) OVER (ORDER BY c) AS decile FROM a)
        SELECT decile, treatment, count(*), avg(y), var_samp(y) FROM d GROUP BY 1, 2 ORDER BY 1, 2
    """).fetchall()
    by = {}
    for dec, tr, n, m, v in seg:
        by.setdefault(dec, {})[tr] = (n, m, v)
    segments, lifts, ws = [], [], []
    for dec in sorted(by):
        (n0d, m0d, v0d), (n1d, m1d, v1d) = by[dec][0], by[dec][1]
        lift, se = two_arm(n1d, m1d, v1d, n0d, m0d, v0d)
        segments.append({
            "decile": dec, "n_treated": n1d, "n_control": n0d,
            "rate_treated": m1d, "rate_control": m0d,
            "abs_lift": lift, "ci_low": lift - Z * se, "ci_high": lift + Z * se,
            "rel_lift": lift / m0d if m0d > 0 else None,
            "readable": min(n1d * m1d, n0d * m0d) >= 10,
        })
        if se > 0:
            lifts.append(lift); ws.append(1 / se ** 2)
    lifts, ws = np.array(lifts), np.array(ws)
    pooled = float((ws * lifts).sum() / ws.sum())
    q = float((ws * (lifts - pooled) ** 2).sum())
    q_df = len(lifts) - 1
    return {
        "beta": dict(zip(feats, beta.tolist())), "theta": float(theta),
        "n_treated": n1, "n_control": n0,
        "rate_treated": my1, "rate_control": my0,
        "raw": {"abs_lift": raw_lift, "se": raw_se, "ci_low": raw_lift - Z * raw_se,
                "ci_high": raw_lift + Z * raw_se, "rel_lift": raw_lift / my0, "z": raw_lift / raw_se},
        "cuped": {"abs_lift": adj_lift, "se": adj_se, "ci_low": adj_lift - Z * adj_se,
                  "ci_high": adj_lift + Z * adj_se, "rel_lift": adj_lift / my0, "z": adj_lift / adj_se},
        "variance_reduction": var_red,
        "equivalent_sample_size_saving": var_red,
        "ci_width_reduction": 1 - adj_se / raw_se,
        "segments": segments,
        "heterogeneity": {"cochran_q": q, "df": q_df, "p_value": float(chi2.sf(q, q_df))},
    }


def balance(con, feats):
    rows = con.execute(f"""SELECT treatment, {', '.join(f'avg({f}), var_samp({f})' for f in feats)}
                           FROM t GROUP BY 1 ORDER BY 1""").fetchall()
    c, tr = rows[0][1:], rows[1][1:]
    smd = {}
    for i, f in enumerate(feats):
        m0, v0, m1, v1 = c[2 * i], c[2 * i + 1], tr[2 * i], tr[2 * i + 1]
        smd[f] = float((m1 - m0) / np.sqrt((v0 + v1) / 2)) if v0 + v1 > 0 else 0.0
    return {"smd": smd, "max_abs_smd": max(abs(v) for v in smd.values())}


def run(path, feats=FEATURES, expected_rows=EXPECTED_ROWS, threads=None, materialize=True, memory_limit=None):
    con = duckdb.connect()
    con.execute("SET temp_directory='.duckdb_tmp'")
    if memory_limit:
        con.execute(f"SET memory_limit='{memory_limit}'")
    if threads:
        con.execute(f"SET threads={threads}")
    con.execute(f"CREATE VIEW t AS SELECT * FROM read_csv_auto('{path}', header=true)")
    n = con.execute("SELECT count(*) FROM t").fetchone()[0]
    if expected_rows is not None:
        assert n == expected_rows, f"expected {expected_rows} rows, got {n}"
    if materialize:  # faster, needs ~2 GB RAM for the full file; otherwise each pass re-reads the gzip
        con.execute("CREATE TEMP TABLE t2 AS SELECT * FROM t")
        con.execute("DROP VIEW t"); con.execute("ALTER TABLE t2 RENAME TO t")
    out = {"rows": n, "balance": balance(con, feats)}
    for y in OUTCOMES:
        out[y] = analyse(con, y, feats)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--out", default="results/variance_reduction.json")
    ap.add_argument("--low-memory", action="store_true", help="stream from the gzip instead of loading it (Cloud Shell)")
    args = ap.parse_args()
    res = run(args.csv, materialize=not args.low_memory, memory_limit="1500MB" if args.low_memory else None)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(res, indent=2))
    for y in OUTCOMES:
        r = res[y]
        print(f"{y}: raw lift {r['raw']['abs_lift']*100:.4f} pp (se {r['raw']['se']*100:.5f}), "
              f"CUPED lift {r['cuped']['abs_lift']*100:.4f} pp (se {r['cuped']['se']*100:.5f}), "
              f"variance reduction {r['variance_reduction']:.1%}, "
              f"decile heterogeneity Q={r['heterogeneity']['cochran_q']:.1f} p={r['heterogeneity']['p_value']:.3g}")
    print(f"max |SMD| across f0..f11: {res['balance']['max_abs_smd']:.4f}")


if __name__ == "__main__":
    main()
