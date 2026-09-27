"""Compare an enumerated rank/size slice with the published catalogue by isomorphism."""
import argparse
import collections
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sage.matroids.advanced import BasisMatroid
from gf5minors.compact import unpack
from gf5minors.sage_bridge import to_sage

parser = argparse.ArgumentParser()
parser.add_argument("directories", type=Path, nargs="+")
args = parser.parse_args()
reference = [json.loads(line) for line in (ROOT/"data/catalogue/gf5-excluded-through10.jsonl").read_text().splitlines()]
for directory in args.directories:
    summary = json.loads((directory/"summary.json").read_text())
    n, r = summary["target_size"], summary["target_rank"]
    assert summary["global_complete"], "Calibration search is incomplete"
    expected = [record for record in reference if record["n"] == n and record["rank"] == r]
    actual = [json.loads(line) for line in (directory/"excluded.jsonl").read_text().splitlines()]
    buckets = collections.defaultdict(list)
    for i, record in enumerate(expected):
        m = BasisMatroid(to_sage(unpack(record, validate=False)))
        buckets[m._bases_invariant()].append((i, m))
    matched = []
    for record in actual:
        m = BasisMatroid(to_sage(unpack(record, validate=False)))
        matches = [i for i, known in buckets[m._bases_invariant()] if m.is_isomorphic(known)]
        assert len(matches) == 1, (n, matches, record)
        matched.extend(matches)
    assert sorted(matched) == list(range(len(expected))), (n, len(actual), len(expected))
    report = {"size": n, "rank": r, "classes": len(actual), "exact_isomorphism_match": True,
              "reference": "data/catalogue/gf5-excluded-through10.jsonl"}
    (directory/"catalogue-comparison.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps(report), flush=True)
