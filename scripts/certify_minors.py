"""Export and independently check GF(5) matrices for every immediate minor."""
import argparse
import collections
from hashlib import sha256
import json
from pathlib import Path
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sage.all import GF, Matroid, matrix
from sage.matroids.advanced import BasisMatroid
from gf5minors.compact import unpack
from gf5minors.matroid import verify_representation
from gf5minors.sage_bridge import to_sage

parser = argparse.ArgumentParser()
parser.add_argument("input", type=Path)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--start", type=int, default=0)
parser.add_argument("--stop", type=int)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
records = [json.loads(line) for line in args.input.read_text().splitlines()]
stop = min(args.stop or len(records), len(records))
catalogues = {}

def catalogue(rank, size):
    key = rank, size
    if key not in catalogues:
        directory = ROOT/("data/parents" if rank == 4 else "data/parents-r3")
        path = directory/f"representations-r{rank}-n{size}.jsonl"
        entries = [json.loads(line)["matrix"] for line in path.read_text().splitlines()]
        buckets = collections.defaultdict(list)
        for raw in entries:
            m = BasisMatroid(Matroid(matrix=matrix(GF(5), raw)))
            buckets[m._bases_invariant()].append((m, raw))
        catalogues[key] = buckets
    return catalogues[key]

def witness(m):
    simple = BasisMatroid(m.simplify())
    r, k = simple.full_rank(), simple.size()
    if k == r:
        labels = sorted(map(int, simple.groundset()))
        vectors = {label:[int(i == j) for i in range(r)] for j, label in enumerate(labels)}
    else:
        for candidate, raw in catalogue(r, k)[simple._bases_invariant()]:
            match, mapping = candidate.is_isomorphic(simple, certificate=True)
            if match:
                vectors = {int(mapping[j]):[int(row[j]) for row in raw] for j in range(k)}
                break
        else:
            raise AssertionError("Minor has no GF(5) representation in complete catalogue")
    result = [[0]*m.size() for _ in range(r)]
    for e in range(m.size()):
        if m.rank([e]) == 0:
            continue
        representative = next(f for f in vectors if m.rank([e,f]) == 1)
        for i in range(r):
            result[i][e] = vectors[representative][i]
    assert Matroid(matrix=matrix(GF(5),result)).equals(m)
    return result

started = monotonic()
verified = 0
with (args.output/"minor-witnesses.jsonl").open("x") as output:
    for index in range(args.start, stop):
        m = unpack(records[index])
        assert BasisMatroid(to_sage(m)).is_valid()
        witnesses = []
        for operation in ("delete", "contract"):
            for e in range(m.n):
                minor = m.minor(e, operation)
                raw = witness(BasisMatroid(to_sage(minor)))
                assert verify_representation(minor, raw), "Independent Gaussian check failed"
                witnesses.append({"operation":operation,"element":e,"matrix":raw})
                verified += 1
        report = {"index":index,"matroid_id":m.labelled_id(),"matroid":records[index],
                  "all_immediate_minors_checked":True,"witnesses":witnesses}
        output.write(json.dumps(report)+"\n")
        output.flush()
        if index % 10 == 0:
            print(json.dumps({"index":index,"verified_matrices":verified,"seconds":monotonic()-started}),flush=True)
summary = {"input_sha256":sha256(args.input.read_bytes()).hexdigest(),"start":args.start,"stop":stop,
           "matroids_checked":stop-args.start,"matrices_checked":verified,"complete":True,
           "seconds":monotonic()-started}
(args.output/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
print(json.dumps(summary),flush=True)
