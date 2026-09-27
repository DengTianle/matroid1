"""Check coverage/certificates and produce a self-contained classification report."""
import argparse
import collections
from hashlib import sha256
from itertools import combinations
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from gf5minors.compact import unpack
from gf5minors.sage_bridge import canonical_key

parser = argparse.ArgumentParser()
parser.add_argument("directory", type=Path)
args = parser.parse_args()
directory = args.directory
catalogue = directory/"excluded.jsonl"
records = [json.loads(line) for line in catalogue.read_text().splitlines()]
search = json.loads((directory/"summary.json").read_text())
assert (search["size"],search["rank"]) == (11,4)
assert search["search_complete"] and search["excluded_classes"] == len(records)
digest = sha256(catalogue.read_bytes()).hexdigest()
assert search["catalogue_sha256"] == digest
parent_statuses = collections.Counter()
for shard in search["shards"]:
    for line in (Path(shard["directory"])/"parents.jsonl").read_text().splitlines():
        parent_statuses[json.loads(line)["status"]] += 1
assert sum(parent_statuses.values()) == search["parents_total"]
assert set(parent_statuses).issubset({"EXHAUSTED","DISCONNECTED_PARENT"})
levels = []
for rank,first,parent_directory in ((3,4,"data/parents-r3"),(4,5,"data/parents")):
    for size in range(first,11):
        path = ROOT/parent_directory/f"representations-r{rank}-n{size}.jsonl"
        level = json.loads(path.with_suffix(".summary.json").read_text())
        assert level["complete"]
        assert sum(1 for line in path.open() if line.strip()) == level["representation_classes"]
        abstract = path.with_name(f"abstract-r{rank}-n{size}.jsonl")
        assert sum(1 for line in abstract.open() if line.strip()) == level["abstract_classes"]
        levels.append({**level,"representations_sha256":sha256(path.read_bytes()).hexdigest(),
                       "abstracts_sha256":sha256(abstract.read_bytes()).hexdigest()})
unsat = json.loads((directory/"nonrepresentation/summary.json").read_text())
minors = json.loads((directory/"minors/summary.json").read_text())
for summary in (unsat,minors):
    assert summary["complete"] and summary["input_sha256"] == digest
    assert summary["start"] == 0 and summary["stop"] == len(records)
assert unsat["verified"] == len(records) and not unsat["unknown"]
assert minors["matroids_checked"] == len(records)
assert minors["matrices_checked"] == sum(2*record["n"] for record in records)
proofs = [json.loads(line) for line in (directory/"nonrepresentation/verification.jsonl").read_text().splitlines()]
witnesses = [json.loads(line) for line in (directory/"minors/minor-witnesses.jsonl").read_text().splitlines()]
assert len(proofs) == len(witnesses) == len(records)
keys = set()
statistics = []
for i,(record,proof,witness) in enumerate(zip(records,proofs,witnesses)):
    m = unpack(record,validate=False)
    assert proof["index"] == witness["index"] == i
    assert proof["matroid_id"] == witness["matroid_id"] == m.labelled_id()
    assert proof["status"] == "UNSAT" and proof["proof_checked"]
    assert witness["all_immediate_minors_checked"]
    assert {(item["operation"],item["element"]) for item in witness["witnesses"]} == {
        (operation,e) for operation in ("delete","contract") for e in range(m.n)}
    key = canonical_key(m)
    assert key not in keys, "Duplicate isomorphism class under independent graph canonicalization"
    keys.add(key)
    triangles = [list(t) for t in combinations(range(m.n),3) if m.rank(t) < 3]
    statistics.append({"class_id":record["class_id"],"basis_count":len(m.bases),
                       "triangle_count":len(triangles),"triangles":triangles,
                       "paving":not triangles,"canonical_graph_sha256":sha256(key.encode()).hexdigest()})
calibrations = []
for n in range(7,11):
    report = json.loads((ROOT/f"runs/calibration-n{n}/catalogue-comparison.json").read_text())
    assert report["exact_isomorphism_match"]
    calibrations.append(report)
independent = json.loads((ROOT/"runs/calibration-n10-join/independent-comparison.json").read_text())
assert independent["exact_match"]
verification = {"size":search["size"],"rank":search["rank"],"excluded_classes":len(records),
                "catalogue_sha256":digest,"search_complete":True,
                "parents_covered":search["parents_covered"],"parent_statuses":dict(parent_statuses),
                "parent_catalogue_levels":levels,"all_nonrepresentation_proofs_checked":True,
                "nonrepresentation_proofs":len(proofs),"all_immediate_minor_matrices_checked":True,
                "minor_matrices":minors["matrices_checked"],"independent_isomorphism_deduplication":True,
                "calibration":calibrations,"independent_search_comparison":independent,
                "basis_count_distribution":dict(sorted(collections.Counter(s["basis_count"] for s in statistics).items())),
                "triangle_count_distribution":dict(sorted(collections.Counter(s["triangle_count"] for s in statistics).items())),
                "paving_classes":sum(s["paving"] for s in statistics)}
(directory/"verification.json").write_text(json.dumps(verification,indent=2)+"\n")
(directory/"statistics.json").write_text(json.dumps(statistics,indent=2)+"\n")
descriptions = json.loads((directory/"hyperplanes.json").read_text())
text = [f"There are **{len(records)}** isomorphism classes of rank-four, eleven-element excluded minors for GF(5)-representability in this exhaustive computation.",
        "", "Every class is specified below on the ground set `{0,1,...,10}`. For each class, a four-element set is a **nonbasis if and only if it is contained in one of the listed hyperplanes**. Every other four-element set is a basis. Hyperplanes of size three are omitted, since they contain no four-element sets.",
        "", "The equivalent lexicographic basis-bit records are in [excluded.jsonl](excluded.jsonl), and the hyperplane lists are in [hyperplanes.json](hyperplanes.json). [verification.json](verification.json) records the completed checks. The mathematical completeness argument is in [DELETION_COMPATIBILITY.md](../../docs/DELETION_COMPATIBILITY.md).", "",
        f"The search exhausted all {search['parents_covered']:,} ten-element parent classes. Each listed matroid has a separately encoded determinant-CNF UNSAT proof checked by DRAT-trim and 22 GF(5) matrices for its immediate minors, checked by modular Gaussian elimination and Sage. A second isomorphism check uses canonical colored incidence graphs. Calibration reproduces the published rank-four lists of sizes 7–10 exactly (5, 92, 219, 130).",
        "", "This is a computational classification with executable search code and certificates. It is not a claim of prior peer review or of a formally verified implementation.", "",
        f"Catalogue SHA-256: `{digest}`.", ""]
for description,stats in zip(descriptions,statistics):
    planes = ["{"+",".join(map(str,h))+"}" for h in description["hyperplanes_size_at_least_rank"]]
    text.extend([f"**{description['class_id']}** — {description['basis_count']} bases; {stats['triangle_count']} triangles.",
                 "", "; ".join(planes)+".", ""])
(directory/"CATALOGUE.md").write_text("\n".join(text))
search["independent_candidate_certificates_complete"] = True
(directory/"summary.json").write_text(json.dumps(search,indent=2)+"\n")
print(json.dumps(verification),flush=True)
