"""Raw-input contract check run before dbt: every expected file exists, has the expected
columns, and matches the SHA-256 recorded in raw/MANIFEST.sha256 (written by --record)."""
import hashlib
import sys
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "raw" / "MANIFEST.sha256"
EXPECTED_COLS = {"criteo": {"row_id", "y", "w"},
                 "ads": {"ad_id", "xyz_campaign_id", "fb_campaign_id", "age", "gender", "interest",
                         "Impressions", "Clicks", "Spent", "Total_Conversion", "Approved_Conversion"}}


def files():
    return sorted((ROOT / "raw").rglob("*.parquet")) + sorted((ROOT / "raw").glob("*.csv"))


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    if "--record" in sys.argv:
        MANIFEST.write_text("".join(f"{sha(p)}  {p.relative_to(ROOT)}\n" for p in files()))
        print(f"recorded {len(files())} files")
        return 0
    expected = dict(l.split("  ")[::-1] for l in MANIFEST.read_text().split("\n") if l)
    errors = []
    for rel, digest in expected.items():
        p = ROOT / rel
        if not p.exists():
            errors.append(f"missing {rel}")
            continue
        if sha(p) != digest:
            errors.append(f"checksum changed {rel}")
        if p.suffix == ".parquet" and "criteo/predictions" in rel:
            missing = EXPECTED_COLS["criteo"] - set(pq.read_schema(p).names)
            if missing:
                errors.append(f"{rel} missing columns {missing}")
        if p.suffix == ".csv":
            header = set(p.read_text().split("\n", 1)[0].strip().split(","))
            if EXPECTED_COLS["ads"] - header:
                errors.append(f"{rel} missing columns {EXPECTED_COLS['ads'] - header}")
    print("\n".join(errors) or f"raw contract OK ({len(expected)} files)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
