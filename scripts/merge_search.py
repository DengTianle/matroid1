"""Audit exhaustive shard coverage, deduplicate, and export an exact catalogue."""
import argparse
import collections
from hashlib import sha256
from itertools import combinations
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
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
buckets = collections.defaultdict(list)
classes = []
covered = set()
shards = []
inputs = None
critical_sources = None
total_candidates = 0
for directory in args.directories:
    summary = json.loads((directory/"summary.json").read_text())
    assert summary["complete_for_range"] and not summary["unknown_parents"], directory
    n, r, total = summary["target_size"], summary["target_rank"], summary["parents_total"]
    assert r == 4
    if shards:
        assert (n,r,total) == (shards[0]["target_size"],shards[0]["target_rank"],shards[0]["parents_total"])
    log = [json.loads(line) for line in (directory/"parents.jsonl").read_text().splitlines()]
    parents = [entry["parent"] for entry in log]
    assert sorted(parents) == list(range(summary["start"],summary["stop"])), directory
    assert not covered.intersection(parents), "Overlapping shard ranges"
    assert all(entry["status"] in ("EXHAUSTED","DISCONNECTED_PARENT") for entry in log)
    covered.update(parents)
    run_manifest = json.loads((directory/"manifest.json").read_text())
    sources = {key:value for key,value in run_manifest["sources"].items()
               if key.startswith("gf5minors/") or key in ("scripts/search_compatible_deletions.py","scripts/table_worker.py")}
    if inputs is None:
        inputs,critical_sources = run_manifest["inputs"],sources
    assert inputs == run_manifest["inputs"] and critical_sources == sources, "Shard inputs/code differ"
    total_candidates += summary["deletion_minimal_candidates"]
    for line in (directory/"excluded.jsonl").read_text().splitlines():
        record = json.loads(line)
        assert (record["n"],record["rank"]) == (n,r)
        m = BasisMatroid(to_sage(unpack(record,validate=False)))
        assert m.is_valid() and m.is_3connected()
        bucket = buckets[m._bases_invariant()]
        if any(m.is_isomorphic(previous) for previous in bucket):
            continue
        bucket.append(m)
        classes.append(record)
    shards.append({"directory":str(directory),**summary})
assert covered == set(range(total)), (len(covered),total)
for relative,digest in inputs.items():
    assert sha256((ROOT/relative).read_bytes()).hexdigest() == digest
classes.sort(key=lambda record:int(record["bits"],16))
descriptions = []
for index,record in enumerate(classes,1):
    record["class_id"] = f"GF5-r{r}-n{n}-{index:04d}"
    pure = unpack(record,validate=False)
    m = BasisMatroid(to_sage(pure))
    hyperplanes = sorted(sorted(map(int,h)) for h in m.hyperplanes() if len(h) >= r)
    expected = {frozenset(b) for b in combinations(range(n),r)
                if not any(set(b).issubset(h) for h in hyperplanes)}
    assert expected == pure.bases, "Hyperplane description does not reconstruct the matroid"
    descriptions.append({"class_id":record["class_id"],"n":n,"rank":r,
                         "basis_count":len(pure.bases),"hyperplanes_size_at_least_rank":hyperplanes})
path = args.output/"excluded.jsonl"
path.write_text("".join(json.dumps(record,sort_keys=True)+"\n" for record in classes))
(args.output/"hyperplanes.json").write_text(json.dumps(descriptions,indent=2)+"\n")
report = {"size":n,"rank":r,"excluded_classes":len(classes),"parents_covered":len(covered),
          "parents_total":total,"deletion_minimal_candidates":total_candidates,
          "search_complete":True,"independent_candidate_certificates_complete":False,
          "catalogue_sha256":sha256(path.read_bytes()).hexdigest(),"inputs":inputs,
          "critical_sources":critical_sources,"shards":shards}
(args.output/"summary.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps({key:value for key,value in report.items() if key not in ("shards","inputs","critical_sources")}),flush=True)
