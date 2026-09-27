"""Import only a pinned, inspected Sage archive using an explicit class allowlist."""
import collections
from hashlib import sha256
import io
import json
from pathlib import Path
import pickle
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sage.all import *
from sage.matroids import unpickling
from sage.rings.integer import make_integer
from gf5minors.compact import pack_sage


ALLOWED = {"unpickle_basis_matroid", "unpickle_binary_matrix", "unpickle_binary_matroid",
           "unpickle_circuit_closures_matroid", "unpickle_dual_matroid", "unpickle_minor_matroid",
           "unpickle_ternary_matrix", "unpickle_ternary_matroid"}


class CatalogueUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if module == "sage.matroids.unpickling" and name in ALLOWED:
            return getattr(unpickling, name)
        if module == "sage.rings.integer" and name == "make_integer":
            return make_integer
        if module == "__builtin__" and name == "frozenset":
            return frozenset
        raise pickle.UnpicklingError(f"unapproved pickle global: {module}.{name}")


raw = (ROOT / "data/raw/brettell/gf5_excluded_minors10.sobj").read_bytes()
digest = sha256(raw).hexdigest()
assert digest == "9aa082356eb700a5d60ae2bc24c3ae310e40c4219c9835ff4083a58f0f409465"
catalogue = CatalogueUnpickler(io.BytesIO(zlib.decompress(raw)), encoding="latin1").load()
expected = json.loads((ROOT / "data/known_counts.json").read_text())["counts_by_size_and_rank"]
counts = collections.Counter()
records = []
for index, m in enumerate(catalogue):
    assert m.is_valid()
    counts[int(m.size()), int(m.full_rank())] += 1
    record = pack_sage(m)
    record["catalogue_index"] = index
    records.append(record)
actual = {str(n): {str(r): count for (nn, r), count in sorted(counts.items()) if nn == n}
          for n in sorted({n for n, r in counts})}
assert actual == expected, (actual, expected)
path = ROOT / "data/catalogue/gf5-excluded-through10.jsonl"
path.parent.mkdir(parents=True, exist_ok=True)
if path.exists():
    raise FileExistsError(path)
path.write_text("".join(json.dumps(record, sort_keys=True) + "\n" for record in records))
report = {"source_sha256": digest, "records": len(records), "counts": actual,
          "all_matroids_valid": True, "counts_match_publication": True,
          "representability_rechecked": False}
path.with_suffix(".audit.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2), flush=True)
