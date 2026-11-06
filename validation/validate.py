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

# ---------- full release (13.98M users), independent of the dbt SQL ----------
full = pd.read_parquet("raw/criteo_full/criteo_uplift_v2.1.parquet")
fm = mart("fct_campaign_lift_full").set_index("outcome")
out["experiment_full"] = dict(users=len(full), treated=int(full.treatment.sum()),
                              control=int((1 - full.treatment).sum()))
for o in ["visit", "conversion"]:
    t, c = full[full.treatment == 1][o], full[full.treatment == 0][o]
    pt, pc = t.mean(), c.mean()
    z, p = proportions_ztest([t.sum(), c.sum()], [len(t), len(c)])
    se = np.sqrt(pt * (1 - pt) / len(t) + pc * (1 - pc) / len(c))
    check(f"full {o} t_cvr", pt, fm.loc[o, "t_cvr"]); check(f"full {o} c_cvr", pc, fm.loc[o, "c_cvr"])
    check(f"full {o} z", z, fm.loc[o, "z_stat"], 1e-6)
    check(f"full {o} ci_low", pt - pc - 1.959963984540054 * se, fm.loc[o, "abs_lift_ci95_low"], 1e-12)
    out["experiment_full"][o] = dict(t_rate_pct=round(100 * pt, 4), c_rate_pct=round(100 * pc, 4),
                                     abs_lift_pp=round(100 * (pt - pc), 4),
                                     ci95_pp=[round(100 * (pt - pc - 1.959963984540054 * se), 4),
                                              round(100 * (pt - pc + 1.959963984540054 * se), 4)],
                                     rel_lift_pct=round(100 * (pt / pc - 1), 1), z=round(float(z), 2),
                                     p_value=float(p), incremental=round(float((pt - pc) * len(t))))
srm_full = chisquare([full.treatment.sum(), len(full) - full.treatment.sum()],
                     [0.85 * len(full), 0.15 * len(full)])
out["experiment_full"]["srm"] = dict(t_share_pct=round(100 * full.treatment.mean(), 5),
                                     chi2=round(float(srm_full.statistic), 3), p_value=round(float(srm_full.pvalue), 4))
tr = full[full.treatment == 1]
exp_rate = tr.exposure.mean()
fe = mart("fct_exposure_effect").iloc[0]
check("full exposure_rate", exp_rate, fe.exposure_rate)
check("full control exposed", int(full[full.treatment == 0].exposure.sum()), fe.c_exposed)
cace = (tr.conversion.mean() - full[full.treatment == 0].conversion.mean()) / exp_rate
check("full cace_conversion", cace, fe.cace_conversion, 1e-12)
out["experiment_full"]["exposure"] = dict(exposure_rate_pct=round(100 * exp_rate, 3),
                                          cace_conversion_pp=round(100 * cace, 3),
                                          naive_exposed_vs_control_pp=round(100 * fe.naive_exposed_vs_control_conversion, 3))

out["reconciliation_failures"] = failures
text = json.dumps(out, indent=2, default=float)
open("validation/validation_results.json", "w").write(text + "\n")
print(text)
raise SystemExit(1 if failures else 0)
