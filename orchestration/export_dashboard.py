"""Build Tableau-ready CSVs from the dbt marts and a .twb workbook that reads them.

Usage: python3 src/build_tableau.py <windows_dir_for_csvs>
Writes tableau/*.csv and tableau/Ad_Measurement.twb.
"""
import sys
import uuid
from pathlib import Path
from xml.sax.saxutils import quoteattr

import duckdb

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tableau"
WIN_DIR = sys.argv[1] if len(sys.argv) > 1 else "C:/Users/amarg/adlift-dbt/tableau"

# ---------------------------------------------------------------- CSV extracts (from the dbt marts)
DB = ROOT / "ad_measurement.duckdb"
EXTRACTS = {
    "lift_rates": """
        SELECT (upper(outcome[1]) || outcome[2:]) AS outcome, 'Targeted' AS arm, t_cvr AS rate, t_users AS users FROM main_marts.fct_campaign_lift_full
        UNION ALL
        SELECT (upper(outcome[1]) || outcome[2:]), 'Control', c_cvr, c_users FROM main_marts.fct_campaign_lift_full
        ORDER BY 1, 2 DESC""",
    "lift_readout": """
        WITH l AS (SELECT * FROM main_marts.fct_campaign_lift_full)
        SELECT (upper(outcome[1]) || outcome[2:]) AS outcome, '1. Absolute lift (pp)' AS stat, printf('%+.3f', 100 * abs_lift) AS value FROM l
        UNION ALL SELECT (upper(outcome[1]) || outcome[2:]), '2. 95% CI (pp)', printf('%.3f to %.3f', 100 * abs_lift_ci95_low, 100 * abs_lift_ci95_high) FROM l
        UNION ALL SELECT (upper(outcome[1]) || outcome[2:]), '3. Relative lift', printf('%+.1f%%', 100 * rel_lift) FROM l
        UNION ALL SELECT (upper(outcome[1]) || outcome[2:]), '4. z', printf('%.2f', z_stat) FROM l
        UNION ALL SELECT (upper(outcome[1]) || outcome[2:]), '5. Incremental', printf('%,.0f', incremental_conversions) FROM l
        ORDER BY 1, 2""",
    "replication": """
        SELECT (upper(outcome[1]) || outcome[2:]) AS outcome, 'Sample ' || sample_seed AS sample, rel_lift,
               abs_lift_ci95_low, abs_lift_ci95_high, c_conv AS control_positives
        FROM main_marts.fct_lift_by_sample ORDER BY 1, 2""",
    "assignment_qa": """
        SELECT 'Sample ' || sample_seed AS sample, users, t_share, design_t_share FROM main_marts.fct_assignment_qa
        UNION ALL
        SELECT 'Full release', users, t_share, design_t_share FROM main_marts.fct_assignment_qa_full ORDER BY 1""",
    "exposure_effect": """
        WITH e AS (SELECT * FROM main_marts.fct_exposure_effect)
        SELECT '1. Effect per targeted user (ITT, causal)' AS estimate, itt_conversion AS conversion_lift_pp FROM e
        UNION ALL SELECT '2. Effect per exposed user (Wald/CACE, causal)', cace_conversion FROM e
        UNION ALL SELECT '3. Exposed vs control (naive, not causal)', naive_exposed_vs_control_conversion FROM e
        ORDER BY 1""",
    "campaign_efficiency": """
        SELECT 'Campaign ' || campaign_id AS campaign, ads, spend_usd, round(spend_usd / sum(spend_usd) OVER (), 4) AS spend_share,
               ctr, cpc_usd, approved_conversions, cost_per_approved_conversion_usd
        FROM main_marts.agg_campaign_performance ORDER BY spend_usd DESC""",
    "segment_cpa": """
        SELECT age_band, gender, sum(spend_usd) AS spend_usd, sum(approved_conversions) AS approved_conversions,
               round(sum(spend_usd) / nullif(sum(approved_conversions), 0), 2) AS cost_per_approved_conversion_usd
        FROM main_marts.agg_campaign_segment_performance WHERE campaign_id = 1178
        GROUP BY 1, 2 ORDER BY 1, 2""",
    "kpis": """
        WITH l AS (SELECT * FROM main_marts.fct_campaign_lift_full), c AS (SELECT * FROM main_marts.agg_campaign_performance)
        SELECT * FROM (VALUES
          (1, 'users in the experiment', printf('%,d', (SELECT max(t_users + c_users)::BIGINT FROM l))),
          (2, 'visit lift', (SELECT printf('%+.1f%%', 100 * rel_lift) FROM l WHERE outcome = 'visit')),
          (3, 'conversion lift', (SELECT printf('%+.1f%%', 100 * rel_lift) FROM l WHERE outcome = 'conversion')),
          (4, 'incremental conversions', (SELECT printf('%,.0f', incremental_conversions) FROM l WHERE outcome = 'conversion')),
          (5, 'of ad spend in the least efficient campaign',
              (SELECT printf('%.0f%%', 100 * max(spend_usd) / sum(spend_usd)) FROM c))
        ) t(sort_order, metric, value)""",
}

DIM_S = ("string", "dimension", "nominal")
MEA_I = ("integer", "measure", "quantitative")
MEA_R = ("real", "measure", "quantitative")
COLS = {
    "lift_rates": {"outcome": DIM_S, "arm": DIM_S, "rate": MEA_R, "users": MEA_R},
    "lift_readout": {"outcome": DIM_S, "stat": DIM_S, "value": DIM_S},
    "replication": {"outcome": DIM_S, "sample": DIM_S, "rel_lift": MEA_R, "abs_lift_ci95_low": MEA_R,
                    "abs_lift_ci95_high": MEA_R, "control_positives": MEA_R},
    "assignment_qa": {"sample": DIM_S, "users": MEA_I, "t_share": MEA_R, "design_t_share": MEA_R},
    "exposure_effect": {"estimate": DIM_S, "conversion_lift_pp": MEA_R},
    "campaign_efficiency": {"campaign": DIM_S, "ads": MEA_I, "spend_usd": MEA_R, "spend_share": MEA_R, "ctr": MEA_R,
                            "cpc_usd": MEA_R, "approved_conversions": MEA_R, "cost_per_approved_conversion_usd": MEA_R},
    "segment_cpa": {"age_band": DIM_S, "gender": DIM_S, "spend_usd": MEA_R, "approved_conversions": MEA_R,
                    "cost_per_approved_conversion_usd": MEA_R},
    "kpis": {"sort_order": MEA_I, "metric": DIM_S, "value": DIM_S},
}
CAPTIONS = {"outcome": "Outcome", "arm": "Arm", "rate": "Rate", "stat": "Statistic", "value": "Value",
            "sample": "Sample", "rel_lift": "Relative lift", "t_share": "Treatment share",
            "campaign": "Campaign", "spend_share": "Share of spend", "cost_per_approved_conversion_usd": "Cost per approved conversion ($)",
            "age_band": "Age", "gender": "Gender", "spend_usd": "Spend ($)",
            "estimate": "Estimate", "conversion_lift_pp": "Conversion lift"}
PERCENT = {"rate", "rel_lift", "t_share", "design_t_share", "spend_share", "ctr", "conversion_lift_pp"}


def export():
    OUT.mkdir(exist_ok=True)
    for f in OUT.glob("*.csv"):
        f.unlink()
    con = duckdb.connect(str(DB), read_only=True)
    for name, sql in EXTRACTS.items():
        rel = con.sql(sql)
        assert list(rel.columns) == list(COLS[name]), (name, rel.columns)
        rel.write_csv(str(OUT / f"{name}.csv"))
    con.close()


# ---------------------------------------------------------------- TWB
def ds_id(name):
    return f"federated.{name}"


DS_PALETTES = {}  # ds -> {field: {value: color}}


def datasource(name):
    cols = COLS[name]
    pal = DS_PALETTES.get(name, {})
    pal_xml = ""
    if pal:
        rules = "".join(
            f"<encoding attr='color' field='[none:{f}:nk]' type='palette'>"
            + "".join(f"<map to='{c}'><bucket>&quot;{v}&quot;</bucket></map>" for v, c in m.items())
            + "</encoding>" for f, m in pal.items())
        pal_xml = f"\n      <style><style-rule element='mark'>{rules}</style-rule></style>"
    rel_cols = "\n".join(
        f"            <column datatype='{dt}' name='{c}' ordinal='{i}' />"
        for i, (c, (dt, _, _)) in enumerate(cols.items()))
    def meta_col(c, dt, role, typ):
        cap = f" caption={quoteattr(CAPTIONS[c])}" if c in CAPTIONS else ""
        fmt = " default-format='p0%'" if c in PERCENT else ""
        return f"      <column{cap} datatype='{dt}'{fmt} name='[{c}]' role='{role}' type='{typ}' />"
    meta = "\n".join(meta_col(c, *v) for c, v in cols.items())
    return f"""    <datasource caption='{name}' inline='true' name='{ds_id(name)}' version='18.1'>
      <connection class='federated'>
        <named-connections>
          <named-connection caption='{name}' name='textscan.{name}'>
            <connection class='textscan' directory={quoteattr(WIN_DIR)} filename='{name}.csv' password='' server='' />
          </named-connection>
        </named-connections>
        <relation connection='textscan.{name}' name='{name}.csv' table='[{name}#csv]' type='table'>
          <columns character-set='UTF-8' header='yes' locale='en_US' separator=','>
{rel_cols}
          </columns>
        </relation>
      </connection>
{meta}{pal_xml}
    </datasource>"""


def inst(field, deriv, kind):
    """column-instance name like [sum:asked:qk]."""
    prefix = {"None": "none", "Sum": "sum", "Avg": "avg", "Attribute": "attr"}[deriv]
    return f"[{prefix}:{field}:{kind}]"


def worksheet(title, ds, deps, rows, cols, mark, encodings="", sort=None, filters="",
              palette=None, cell_size=None, subtitle=""):
    """deps: list of (field, derivation, kind) tuples used by the sheet."""
    c = COLS[ds]
    dep_cols = "\n".join(
        f"            <column datatype='{c[f][0]}' name='[{f}]' role='{c[f][1]}' type='{c[f][2]}' />"
        for f in dict.fromkeys(f for f, _, _ in deps))
    typ = {"nk": "nominal", "ok": "ordinal", "qk": "quantitative"}
    dep_inst = "\n".join(
        f"            <column-instance column='[{f}]' derivation='{d}' name='{inst(f, d, k)}' pivot='key' type='{typ[k]}' />"
        for f, d, k in deps)
    D = ds_id(ds)
    ref = lambda f, d, k: f"[{D}].{inst(f, d, k)}"
    enc = "".join(f"<{a} column='{ref(*x)}' />" for a, x in encodings) if encodings else ""
    sort_xml = ""
    if sort:
        dim, measure, direction = sort
        lvl = inst(*dim)
        sort_xml = (f"          <filter class='categorical' column='{ref(*dim)}'><groupfilter function='level-members' level='{lvl}' user:ui-enumeration='all' user:ui-marker='enumerate' /></filter>\n"
                    f"          <computed-sort column='{ref(*dim)}' direction='{direction}' using='{ref(*measure)}' />\n")
    rules = []
    if palette:
        field, mapping = palette
        pass  # Tableau 2026.2 ignored hand-written color maps; subtitles describe the default colors instead
    if cell_size:
        rules.append(f"<style-rule element='cell'><format attr='font-size' value='{cell_size}' /><format attr='font-weight' value='bold' /></style-rule>")
    style = f"<style>{''.join(rules)}</style>" if rules else "<style />"
    sub = f"<run fontsize='9' fontcolor='#6b7280'>&#10;{subtitle}</run>" if subtitle else ""
    return f"""    <worksheet name={quoteattr(title)}>
      <layout-options><title><formatted-text><run bold='true'>{title}</run>{sub}</formatted-text></title></layout-options>
      <table>
        <view>
          <datasources><datasource caption='{ds}' name='{D}' /></datasources>
          <datasource-dependencies datasource='{D}'>
{dep_cols}
{dep_inst}
          </datasource-dependencies>
{filters}{sort_xml}          <aggregation value='true' />
        </view>
        {style}
        <panes>
          <pane selection-relaxation-option='selection-relaxation-allow'>
            <view><breakdown value='auto' /></view>
            <mark class='{mark}' />
            {"<encodings>" + enc + "</encodings>" if enc else ""}
          </pane>
        </panes>
        <rows>{' / '.join(ref(*r) for r in rows)}</rows>
        <cols>{' / '.join(ref(*x) for x in cols)}</cols>
      </table>
      <simple-id uuid='{{{str(uuid.uuid4()).upper()}}}' />
    </worksheet>"""


SHEETS = []


def sheet(*a, **k):
    SHEETS.append((a[0], worksheet(*a, **k)))


BLUE, AMBER, GREY, GREEN, RED = "#2f5d8a", "#c98a2b", "#b8c2cf", "#2e7d4f", "#b4433a"


def build_sheets():
    sheet("Targeted vs Control", "lift_rates",
          [("outcome", "None", "nk"), ("arm", "None", "nk"), ("rate", "Sum", "qk")],
          rows=[("outcome", "None", "nk"), ("arm", "None", "nk")], cols=[("rate", "Sum", "qk")], mark="Bar",
          encodings=[("color", ("arm", "None", "nk")), ("text", ("rate", "Sum", "qk"))],
          subtitle="Full Criteo release, 13,979,592 users randomly targeted by ads (85%) or withheld (15%).")
    sheet("Lift Replication by Sample", "replication",
          [("outcome", "None", "nk"), ("sample", "None", "nk"), ("rel_lift", "Sum", "qk")],
          rows=[("sample", "None", "nk")], cols=[("outcome", "None", "nk"), ("rel_lift", "Sum", "qk")], mark="Bar",
          encodings=[("text", ("rel_lift", "Sum", "qk"))],
          subtitle="Three 2% samples. Visit lift is stable; conversion lift swings (64-103 control conversions per sample).")
    sheet("Assignment QA", "assignment_qa",
          [("sample", "None", "nk"), ("t_share", "Sum", "qk")],
          rows=[("sample", "None", "nk")], cols=[("t_share", "Sum", "qk")], mark="Text",
          encodings=[("text", ("t_share", "Sum", "qk"))],
          subtitle="Treatment share vs the 85% design. No sample-ratio mismatch.")
    sheet("Effect per Exposed User", "exposure_effect",
          [("estimate", "None", "nk"), ("conversion_lift_pp", "Sum", "qk")],
          rows=[("estimate", "None", "nk")], cols=[("conversion_lift_pp", "Sum", "qk")], mark="Bar",
          encodings=[("text", ("conversion_lift_pp", "Sum", "qk"))],
          subtitle="Only 3.6% of targeted users saw an ad. The naive comparison overstates the causal effect.")
    sheet("Cost per Approved Conversion", "campaign_efficiency",
          [("campaign", "None", "nk"), ("cost_per_approved_conversion_usd", "Sum", "qk"), ("spend_share", "Sum", "qk")],
          rows=[("campaign", "None", "nk")], cols=[("cost_per_approved_conversion_usd", "Sum", "qk")], mark="Bar",
          encodings=[("text", ("cost_per_approved_conversion_usd", "Sum", "qk")), ("tooltip", ("spend_share", "Sum", "qk"))],
          subtitle="Facebook ad export, 1,143 ads. Ratio of sums, never an average of per-ad ratios.")
    sheet("Campaign 1178 by Segment", "segment_cpa",
          [("age_band", "None", "nk"), ("gender", "None", "nk"), ("cost_per_approved_conversion_usd", "Sum", "qk")],
          rows=[("age_band", "None", "nk")], cols=[("gender", "None", "nk"), ("cost_per_approved_conversion_usd", "Sum", "qk")],
          mark="Bar", encodings=[("text", ("cost_per_approved_conversion_usd", "Sum", "qk"))],
          subtitle="The campaign with most of the spend, split by age band and gender.")


def dashboard():
    # 1400 x 1100 fixed. Rows: KPIs | lift + readout | replication + QA | campaign + segment
    W, H = 1400, 1100
    # Zone geometry is in Tableau's 0-100000 relative units, not pixels.
    sx = lambda px: round(px * 100000 / W)
    sy = lambda px: round(px * 100000 / H)
    zid = iter(range(10, 100))
    z = []
    z.append(f"<zone h='{sy(50)}' id='{next(zid)}' type-v2='title' w='100000' x='0' y='0' />")
    layout = [
        (150, 300, [("Targeted vs Control", 700)]),
        (450, 280, [("Lift Replication by Sample", 520), ("Effect per Exposed User", 560), ("Assignment QA", 320)]),
        (730, 370, [("Cost per Approved Conversion", 600), ("Campaign 1178 by Segment", 800)]),
    ]
    for y, h, cells in layout:
        x = 0
        for name, w in cells:
            z.append(f"<zone h='{sy(h)}' id='{next(zid)}' name={quoteattr(name)} type-v2='visual' w='{sx(w)}' x='{sx(x)}' y='{sy(y)}' />")
            x += w
    import csv
    rows = list(csv.DictReader(open(OUT / "kpis.csv")))
    runs = "".join(
        f"<run bold='true' fontcolor='#1c2230' fontsize='18'>{r['value']}</run>"
        f"<run fontcolor='#5d6678' fontsize='11'> {r['metric']}{'    |    ' if i < len(rows) - 1 else ''}</run>"
        for i, r in enumerate(rows))
    note = ("<run fontcolor='#5d6678' fontsize='10'>&#10;Criteo Uplift v2.1 randomized test, full 13.98M-user release (Diemert et al., AdKDD 2018), and a "
            "Facebook ad campaign export. Built with dbt; every figure re-checked by an independent pandas/statsmodels recomputation.</run>")
    z.insert(1, f"<zone h='{sy(100)}' id='{next(zid)}' type-v2='text' w='100000' x='0' y='{sy(50)}'>"
                f"<formatted-text>{runs}{note}</formatted-text></zone>")
    readout = list(csv.DictReader(open(OUT / "lift_readout.csv")))
    lines = ["<run bold='true' fontcolor='#1c2230' fontsize='15'>Lift readout (full release)</run>",
             "<run fontcolor='#5d6678' fontsize='10'>&#10;Two-proportion z-test; 95% CI on the absolute difference.&#10;</run>"]
    for outcome in ["Visit", "Conversion"]:
        vals = {r["stat"]: r["value"] for r in readout if r["outcome"] == outcome}
        lines.append(f"<run bold='true' fontcolor='#1c2230' fontsize='12'>&#10;{outcome}: {vals['3. Relative lift']}</run>"
                     f"<run fontcolor='#1c2230' fontsize='11'>&#10;  absolute {vals['1. Absolute lift (pp)']} pp "
                     f"(95% CI {vals['2. 95% CI (pp)']} pp), z = {vals['4. z']}, ~{vals['5. Incremental']} incremental</run>")
    z.append(f"<zone h='{sy(300)}' id='{next(zid)}' type-v2='text' w='{sx(700)}' x='{sx(700)}' y='{sy(150)}'>"
             f"<formatted-text>{''.join(lines)}</formatted-text></zone>")
    zones = "\n          ".join(z)
    return f"""    <dashboard name='Ad Incrementality and Campaign Efficiency'>
      <size maxheight='{H}' maxwidth='{W}' minheight='{H}' minwidth='{W}' sizing-mode='fixed' />
      <datasources />
      <zones>
        <zone h='100000' id='2' type-v2='layout-basic' w='100000' x='0' y='0'>
          {zones}
        </zone>
      </zones>
      <simple-id uuid='{{{str(uuid.uuid4()).upper()}}}' />
    </dashboard>"""


def windows():
    out = []
    for name, _ in SHEETS:
        out.append(f"    <window class='worksheet' hidden='true' name={quoteattr(name)}><cards><edge name='left'><strip size='160'><card type='pages' /><card type='filters' /><card type='marks' /></strip></edge><edge name='top'><strip size='31'><card type='columns' /></strip><strip size='31'><card type='rows' /></strip><strip size='31'><card type='title' /></strip></edge></cards><simple-id uuid='{{{str(uuid.uuid4()).upper()}}}' /></window>")
    vps = "".join(f"<viewpoint name={quoteattr(n)} />" for n, _ in SHEETS)
    out.append(f"    <window class='dashboard' maximized='true' name='Ad Incrementality and Campaign Efficiency'><viewpoints>{vps}</viewpoints><active id='-1' /><simple-id uuid='{{{str(uuid.uuid4()).upper()}}}' /></window>")
    return "\n".join(out)


def build_twb():
    build_sheets()
    dss = "\n".join(datasource(n) for n in COLS)
    sheets = "\n".join(x for _, x in SHEETS)
    twb = f"""<?xml version='1.0' encoding='utf-8' ?>
<workbook original-version='18.1' source-build='2026.2.0 (20262.26.0528.2205)' source-platform='win' version='18.1' xmlns:user='http://www.tableausoftware.com/xml/user'>
  <document-format-change-manifest>
    <SheetIdentifierTracking />
    <SortTagCleanup />
    <WindowsPersistSimpleIdentifiers />
  </document-format-change-manifest>
  <preferences />
  <datasources>
{dss}
  </datasources>
  <worksheets>
{sheets}
  </worksheets>
  <dashboards>
{dashboard()}
  </dashboards>
  <windows>
{windows()}
  </windows>
</workbook>
"""
    (OUT / "Ad_Measurement.twb").write_text(twb, encoding="utf-8")


if __name__ == "__main__":
    export()
    build_twb()
    print("wrote", sorted(p.name for p in OUT.iterdir()))
