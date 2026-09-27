"""Create/validate project fixtures and record a target-size CNF build only."""
from hashlib import sha256
import json
from pathlib import Path
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from gf5minors.__main__ import atomic_json, provenance
from gf5minors.extensions import encode_extensions
from gf5minors.matroid import fano, vamos, uniform, rank4_fixture


directory = ROOT / "data" / "fixtures"
directory.mkdir(parents=True, exist_ok=True)
fixtures = {"U2_6": uniform(2, 6), "U2_7": uniform(2, 7), "F7": fano(),
            "V8": vamos(), "rank4_11_representable": rank4_fixture()}
for name, matroid in fixtures.items():
    record = matroid.validate().to_record()
    path = directory / f"{name}.json"
    if path.exists():
        if json.loads(path.read_text()) != record:
            raise ValueError(f"existing fixture differs: {path}")
    else:
        atomic_json(path, record)

started = monotonic()
parent = fixtures["rank4_11_representable"].minor(10, "delete")
subsets, clauses = encode_extensions(parent, simple=True, cosimple=True)
assert len(subsets) == 330
assert sum(10 in subset for subset in subsets) == 120
stats = {"kind": "encoding-only; no target-size extension models requested",
         "parent_id": parent.labelled_id(), "variables": len(subsets),
         "free_variables": sum(10 in subset for subset in subsets), "clauses": len(clauses),
         "build_seconds": monotonic() - started, "provenance": provenance()}
atomic_json(Path(sys.argv[1]) / "target-encoding.json", stats)

manifest_path = ROOT / "data" / "reference_manifest.json"
if manifest_path.exists():
    manifest = json.loads(manifest_path.read_text())
    for file in manifest["files"]:
        data = (ROOT / file["path"]).read_bytes()
        assert len(data) == file["bytes"] and sha256(data).hexdigest() == file["sha256"]
    print("Reference checksums verified; no downloaded content executed", flush=True)
print(json.dumps(stats, indent=2), flush=True)
