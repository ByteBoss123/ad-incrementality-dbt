"""Verify the published Sigma workbook against the independently computed results.

Pulls each required element from Sigma as CSV and checks its numbers against
validation/validation_results.json (pandas + statsmodels recomputation from raw
data). Exit code 1 on any mismatch, so it can run in CI after each refresh.

    export SIGMA_CLIENT_ID=... SIGMA_CLIENT_SECRET=... [SIGMA_CLOUD=aws]
    python sigma/verify_workbook.py --workbook "Ad Incrementality & Campaign Efficiency"
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ["Lift Summary", "Campaign Efficiency", "Replication by Sample", "Assignment QA"]


def norm(h: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", h.strip().lower()).strip("_")


def num(v: str) -> float:
    """Parse Sigma CSV values, which may carry %, $, or thousands separators."""
    s = str(v).strip().replace(",", "").replace("$", "")
    if s.endswith("%"):
        return float(s[:-1]) / 100
    return float(s)


def rows_by(rows: list[dict], key: str) -> dict[str, dict]:
    return {str(r[key]).strip().lower(): r for r in ({norm(k): v for k, v in r.items()} for r in rows)}


def expectations(v: dict) -> list[tuple[str, str, str, str, float, float]]:
    """(element, key column, key value, value column, expected, tolerance)."""
    e = v["experiment"]
    out = []
    for o in ["visit", "conversion"]:
        out += [
            ("Lift Summary", "outcome", o, "relative_lift", e[o]["rel_lift_pct"] / 100, 0.0006),
            ("Lift Summary", "outcome", o, "abs_lift_pp", e[o]["abs_lift_pp"], 0.0006),
            ("Lift Summary", "outcome", o, "ci95_low_pp", e[o]["ci95_pp"][0], 0.0006),
            ("Lift Summary", "outcome", o, "ci95_high_pp", e[o]["ci95_pp"][1], 0.0006),
        ]
        for seed, rl in v["replication"][o]["rel_lift_pct_by_seed"].items():
            out.append(("Replication by Sample", "sample_id", f"{o}|{seed}", "relative_lift", rl / 100, 0.0006))
    for cid, c in v["campaigns"].items():
        out.append(("Campaign Efficiency", "campaign", cid, "cost_per_approved_conversion_usd",
                    c["cost_per_approved_conv"], 0.006))
    for seed, s in v["srm"].items():
        out.append(("Assignment QA", "sample_seed", seed, "t_share", s["t_share_pct"] / 100, 0.00001))
    return out


def verify(exports: dict[str, list[dict]], v: dict) -> list[str]:
    errors = [f"missing element: {t}" for t in REQUIRED if t not in exports]
    indexed = {}
    for title, rows in exports.items():
        if title == "Replication by Sample":
            normed = [{norm(k): val for k, val in r.items()} for r in rows]
            indexed[title] = {f"{r['outcome'].strip().lower()}|{str(r['sample_id']).strip()}": r for r in normed}
        elif title in REQUIRED:
            key = {"Lift Summary": "outcome", "Campaign Efficiency": "campaign", "Assignment QA": "sample_seed"}[title]
            indexed[title] = rows_by(rows, key)
    for el, _, kval, col, exp, tol in expectations(v):
        if el not in indexed:
            continue
        row = indexed[el].get(str(kval).lower())
        if row is None:
            errors.append(f"{el}: no row {kval!r}")
            continue
        if col not in row:
            errors.append(f"{el}: missing column {col!r} (have {sorted(row)})")
            continue
        got = num(row[col])
        if abs(got - exp) > tol:
            errors.append(f"{el} [{kval}] {col}: sigma={got} expected={exp}")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workbook", default="Ad Incrementality & Campaign Efficiency")
    ap.add_argument("--results", default=str(ROOT / "validation/validation_results.json"))
    a = ap.parse_args()
    from sigma_client import SigmaClient

    v = json.loads(Path(a.results).read_text())
    client = SigmaClient.from_env()
    wb = client.find_workbook(a.workbook)
    elements = client.elements_by_title(wb["workbookId"])
    exports = {t: client.export_element_csv(wb["workbookId"], elements[t]["elementId"])
               for t in REQUIRED if t in elements}
    errors = verify(exports, v)
    checks = len(expectations(v))
    if errors:
        print(f"FAIL: {len(errors)} problem(s) across {checks} checks")
        print("\n".join(f"  - {e}" for e in errors))
        return 1
    print(f"PASS: Sigma workbook '{a.workbook}' matches all {checks} independently computed values")
    return 0


if __name__ == "__main__":
    sys.exit(main())
