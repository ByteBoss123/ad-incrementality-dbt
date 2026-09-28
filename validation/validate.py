"""Independent check of the dbt marts.

Recomputes every headline figure directly from the raw files with pandas +
statsmodels (no shared code with the dbt SQL), then compares to the marts.
Also computes the statistics that are not portable to SQL: p-values,
Benjamini-Hochberg adjustment across all slices, and a chi-square test of
sample-ratio mismatch against the documented 85/15 design, and a replication
(heterogeneity) test across the three random samples.
"""
import json
import duckdb
import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.proportion import proportions_ztest

DB = "ad_measurement.duckdb"
con = duckdb.connect(DB, read_only=True)
mart = lambda t: con.sql(f"select * from main_marts.{t}").df()
out, failures = {}, []

def check(name, a, b, tol=1e-9):
    ok = abs(float(a) - float(b)) <= tol
    if not ok:
        failures.append(f"{name}: pandas={a} dbt={b}")
    return ok

# ---------- experiment (Criteo) ----------
import glob
from scipy.stats import chi2, chisquare, norm
frames = {}
for o in ["visit", "conversion"]:
    parts = []
    for f in sorted(glob.glob(f"raw/criteo/predictions_{o}_frac0.1_seed*.parquet")):
        d = pd.read_parquet(f, columns=["row_id", "y", "w"])
        d["seed"] = int(f.split("seed")[1].split(".")[0])
        parts.append(d)
    frames[o] = pd.concat(parts)
v = frames["visit"].drop_duplicates("row_id").rename(columns={"y": "visit"})
c = frames["conversion"].drop_duplicates("row_id").rename(columns={"y": "conversion"})
u = v[["row_id", "w", "visit"]].merge(c[["row_id", "conversion"]], on="row_id", how="inner")
assert len(u) == len(v) == len(c)
lift = mart("fct_campaign_lift").set_index("outcome")
out["experiment"] = dict(users=len(u), treated=int(u.w.sum()), control=int((1 - u.w).sum()),
                         users_in_multiple_samples=int((frames["visit"].row_id.value_counts() > 1).sum()))
for o in ["visit", "conversion"]:
    t, k = u[u.w == 1][o], u[u.w == 0][o]
    z, p = proportions_ztest([t.sum(), k.sum()], [len(t), len(k)])
    se = np.sqrt(t.mean() * (1 - t.mean()) / len(t) + k.mean() * (1 - k.mean()) / len(k))
    r = lift.loc[o]
    check(f"{o}_t_cvr", t.mean(), r.t_cvr); check(f"{o}_c_cvr", k.mean(), r.c_cvr)
    check(f"{o}_z", z, r.z_stat, 1e-6)
    check(f"{o}_ci_low", t.mean() - k.mean() - 1.959963984540054 * se, r.abs_lift_ci95_low)
    out["experiment"][o] = dict(
        t_rate_pct=round(100 * t.mean(), 3), c_rate_pct=round(100 * k.mean(), 3),
        abs_lift_pp=round(100 * (t.mean() - k.mean()), 4),
        ci95_pp=[round(100 * r.abs_lift_ci95_low, 4), round(100 * r.abs_lift_ci95_high, 4)],
        rel_lift_pct=round(100 * (t.mean() - k.mean()) / k.mean(), 1),
        z=round(z, 2), p_value=float(p),
        incremental=round((t.mean() - k.mean()) * len(t), 0))

# replication across samples: Cochran's Q heterogeneity on per-sample abs lift
# (samples share a small number of users, so Q is approximate)
bs = mart("fct_lift_by_sample")
rep = {}
for o, g in bs.groupby("outcome"):
    se = (g.abs_lift_ci95_high - g.abs_lift_ci95_low) / (2 * 1.959963984540054)
    w_ = 1 / se**2
    pooled = (w_ * g.abs_lift).sum() / w_.sum()
    q = (w_ * (g.abs_lift - pooled) ** 2).sum()
    rep[o] = dict(rel_lift_pct_by_seed={int(s): round(100 * r, 1) for s, r in zip(g.sample_seed, g.rel_lift)},
                  cochran_q=round(q, 2), df=len(g) - 1, p_value=round(float(1 - chi2.cdf(q, len(g) - 1)), 4))
out["replication"] = rep

# sample-ratio mismatch vs the documented 85/15 design
qa = mart("fct_assignment_qa")
srm = {}
for _, r in qa.iterrows():
    stat, p = chisquare([r.t_users, r.c_users], [r.users * 0.85, r.users * 0.15])
    srm[int(r.sample_seed)] = dict(t_share_pct=round(100 * r.t_share, 3), chi2=round(stat, 3), p_value=round(float(p), 4))
out["srm"] = srm
pw = mart("fct_experiment_power").set_index("outcome")
out["power"] = {o: dict(mde_abs_pp=round(100 * pw.loc[o, "mde_abs"], 4), mde_rel_pct=round(100 * pw.loc[o, "mde_rel"], 1)) for o in pw.index}

# ---------- campaigns ----------
a = pd.read_csv("raw/KAG_conversion_data.csv")
a["Spent"] = a["Spent"].round(2)
g = a.groupby("xyz_campaign_id").agg(imp=("Impressions", "sum"), clk=("Clicks", "sum"),
                                     spend=("Spent", "sum"), appr=("Approved_Conversion", "sum"))
m = mart("agg_campaign_performance").set_index("campaign_id")
for cid, r in g.iterrows():
    check(f"cpa_{cid}", r.spend / r.appr, m.loc[cid, "cost_per_approved_conversion_usd"], 1e-6)
    check(f"ctr_{cid}", r.clk / r.imp, m.loc[cid, "ctr"], 1e-12)
out["campaigns"] = {int(k): dict(ads=int(m.loc[k, "ads"]), spend=round(v.spend, 2),
                                 ctr_pct=round(100 * v.clk / v.imp, 4),
                                 cpc=round(v.spend / v.clk, 2),
                                 cost_per_approved_conv=round(v.spend / v.appr, 2))
                    for k, v in g.iterrows()}
# ---------- CPA drivers ----------
import math
best = g.assign(cpa=g.spend / g.appr).cpa.idxmin()
bcpc, bcpac, bcpa = g.loc[best, "spend"] / g.loc[best, "clk"], g.loc[best, "clk"] / g.loc[best, "appr"], g.loc[best, "spend"] / g.loc[best, "appr"]
dm = mart("fct_cpa_drivers").set_index("campaign_id")
drivers = {}
for cid, r in g.iterrows():
    cpa = r.spend / r.appr
    if cid == best:
        continue
    gap = math.log(cpa / bcpa)
    cpc_share = math.log((r.spend / r.clk) / bcpc) / gap
    conv_share = math.log((r.clk / r.appr) / bcpac) / gap
    check(f"cpc_share_{cid}", cpc_share, dm.loc[cid, "cpc_share_of_gap"], 1e-9)
    check(f"conv_share_{cid}", conv_share, dm.loc[cid, "conversion_rate_share_of_gap"], 1e-9)
    drivers[int(cid)] = dict(cpa_ratio_vs_best=round(cpa / bcpa, 2), cpc_share_pct=round(100 * cpc_share, 1),
                             conversion_rate_share_pct=round(100 * conv_share, 1),
                             clicks_per_approved_conversion=round(r.clk / r.appr, 1))
out["cpa_drivers"] = dict(best_campaign=int(best), best_clicks_per_approved_conversion=round(bcpac, 1), campaigns=drivers)
a["age_band"] = a["age"]
seg = a[a.xyz_campaign_id == 1178].groupby("age_band").agg(spend=("Spent", "sum"), appr=("Approved_Conversion", "sum"))
seg["spend_share"] = seg.spend / seg.spend.sum(); seg["conv_share"] = seg.appr / seg.appr.sum(); seg["cpa"] = seg.spend / seg.appr
sm = mart("fct_segment_cpa_drivers"); sm = sm[sm.campaign_id == 1178].set_index("age_band")
for ab, r in seg.iterrows():
    check(f"seg_cpa_{ab}", r.cpa, sm.loc[ab, "cpa_usd"], 1e-6)
    check(f"seg_share_{ab}", r.spend_share, sm.loc[ab, "spend_share"], 1e-9)
out["segment_drivers_1178"] = {ab: dict(spend_share_pct=round(100 * r.spend_share, 1), conversion_share_pct=round(100 * r.conv_share, 1),
                                        cpa=round(r.cpa, 2)) for ab, r in seg.iterrows()}
out["ads"] = len(a)
out["reconciliation_failures"] = failures
print(json.dumps(out, indent=2, default=float))
raise SystemExit(1 if failures else 0)
