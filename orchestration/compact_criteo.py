"""Column-project the official Criteo Uplift v2.1 file to the four flags this project uses.

Input:  criteo-research-uplift-v2.1.csv.gz (13,979,592 rows; f0..f11, treatment, conversion, visit, exposure)
Output: raw/criteo_full/criteo_uplift_v2.1.parquet with row_id (0-based row position, the same
        convention as the UpliftBench samples), treatment, conversion, visit, exposure.
Also writes raw/criteo_full/source_file.sha256 for provenance.
"""
import gzip
import hashlib
import sys
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

OUT = Path(__file__).resolve().parents[1] / "raw" / "criteo_full"
EXPECTED_HEADER = "f0,f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,treatment,conversion,visit,exposure"


def main(src):
    OUT.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha256(Path(src).read_bytes()).hexdigest()
    (OUT / "source_file.sha256").write_text(f"{h}  {Path(src).name}\n")
    flags = []
    with gzip.open(src, "rt") as f:
        assert f.readline().strip() == EXPECTED_HEADER, "unexpected header"
        for line in f:
            flags.append(line.rstrip("\n").rsplit(",", 4)[1:])
    a = np.array(flags, dtype=np.int8)
    assert len(a) == 13_979_592, len(a)
    pq.write_table(pa.table({"row_id": np.arange(len(a), dtype=np.int64), "treatment": a[:, 0],
                             "conversion": a[:, 1], "visit": a[:, 2], "exposure": a[:, 3]}),
                   OUT / "criteo_uplift_v2.1.parquet", compression="zstd")
    print(f"{len(a):,} rows, source sha256 {h}")


if __name__ == "__main__":
    main(sys.argv[1])
