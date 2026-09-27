"""Create a small set of persistent, inspectable regression artifacts."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gf5minors.__main__ import atomic_json, provenance
from gf5minors.extensions import enumerate_extensions
from gf5minors.matroid import uniform, fano, rank4_fixture
from gf5minors.representation import check_excluded, represent


out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
atomic_json(out / "environment.json", provenance())
for name, parent in [("small-extensions", uniform(2, 3)), ("line-extensions", uniform(2, 6))]:
    directory = out / name
    directory.mkdir(exist_ok=False)
    with (directory / "extensions.jsonl").open("x") as stream:
        def emit(m):
            stream.write(json.dumps(m.to_record()) + "\n")
        report = enumerate_extensions(parent, emit, simple=name == "line-extensions", max_models=10)
    atomic_json(directory / "summary.json", report)
    assert report["complete_for_fixed_labelled_parent"]
    print(name, json.dumps(report), flush=True)
report = check_excluded(fano(), seconds=10, artifact_dir=out / "excluded-F7")
assert report["excluded"] is True
print("F7 excluded-minor check passed; DRAT not independently checked", flush=True)
result = represent(rank4_fixture(), seconds=30, artifact_dir=out / "rank4-11-SAT")
assert result.status == "SAT" and result.witness_checked
print("rank4-11 represented fixture", json.dumps(result.to_record()), flush=True)
