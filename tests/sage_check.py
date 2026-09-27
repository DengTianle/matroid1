"""Independent Sage comparisons, including abstract extension completeness."""
from itertools import combinations
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gf5minors.matroid import fano, vamos, uniform, from_matrix, rank4_fixture
from gf5minors.sage_bridge import to_sage, from_sage, canonical_key
from sage.all import GF, Matroid, matrix, matroids
from sage.env import SAGE_VERSION


fixtures = [fano(), vamos(), uniform(0, 2), uniform(2, 2), rank4_fixture(),
            from_matrix([[1, 1, 0, 0, 0], [0, 0, 1, 1, 0]])]
subset_checks = 0
for m in fixtures:
    sage_m = to_sage(m)
    assert sage_m.is_valid()
    assert from_sage(sage_m) == m
    for size in range(m.n + 1):
        for subset in combinations(range(m.n), size):
            assert sage_m.rank(subset) == m.rank(subset)
            subset_checks += 1
    for e in range(m.n):
        assert from_sage(sage_m.delete(e)) == m.minor(e, "delete")
        assert from_sage(sage_m.contract(e)) == m.minor(e, "contract")
    assert canonical_key(m) == canonical_key(m.relabel(list(reversed(range(m.n)))))
assert to_sage(fano()).is_isomorphic(matroids.catalog.Fano())
assert to_sage(vamos()).is_isomorphic(matroids.catalog.Vamos())
assert canonical_key(uniform(3, 7)) != canonical_key(fano())

# Compare the independent Sage modular-cut extensions with the SAT journal.
run_dir = Path(sys.argv[1])
records = [json.loads(line) for line in (run_dir / "small-extensions" / "extensions.jsonl").read_text().splitlines()]
from gf5minors.matroid import BasisMatroid
sat_extensions = {BasisMatroid.from_record(record) for record in records}
sage_extensions = {from_sage(m) for m in to_sage(uniform(2, 3)).extensions(3)}
assert sat_extensions == sage_extensions

# Check saved witnesses with Sage's finite-field matrices as a third algorithm.
witnesses = 0
for path in (run_dir / "excluded-F7").glob("*/result.json"):
    result = json.loads(path.read_text())
    if result["status"] != "SAT":
        continue
    m = BasisMatroid.from_record(json.loads(path.with_name("matroid.json").read_text()))
    sage_m = Matroid(matrix=matrix(GF(5), result["matrix"]), groundset=list(range(m.n)))
    assert from_sage(sage_m) == m
    witnesses += 1
report = {"sage_version": SAGE_VERSION, "rank_subsets_checked": subset_checks,
          "saved_witnesses_checked": witnesses, "extension_sets_equal": True,
          "canonical_relabeling_checks": len(fixtures), "status": "PASS"}
(run_dir / "sage-validation.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
