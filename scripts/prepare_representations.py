"""Turn all UNlabelled field classes into complete labelled representation sets."""
import argparse
import collections
import json
from pathlib import Path
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sage.all import GF, Graph, Matroid, matrix
from sage.matroids.advanced import BasisMatroid
from gf5minors.compact import unpack
from gf5minors.projective import permute, representation_orbit
from gf5minors.sage_bridge import to_sage


def automorphisms(m):
    n = m.size()
    family = list(m.nonbases()) if len(m.nonbases()) < m.bases_count() else list(m.bases())
    g = Graph()
    g.add_vertices(range(n+len(family)))
    for i, subset in enumerate(family, n):
        g.add_edges((i, int(e)) for e in subset)
    partition = [list(range(n)), list(range(n,n+len(family)))]
    group = g.automorphism_group(partition=[p for p in partition if p])
    return [[int(generator(i)) for i in range(n)] for generator in group.gens()]


parser = argparse.ArgumentParser()
parser.add_argument("--size", type=int, required=True)
parser.add_argument("--directory", type=Path, default=ROOT/"data/parents")
args = parser.parse_args()
n = args.size
output = args.directory/f"labelled-r4-n{n}.jsonl"
if output.exists():
    raise FileExistsError(output)
started = monotonic()
records = [json.loads(line) for line in (args.directory/f"abstract-r4-n{n}.jsonl").read_text().splitlines()]
parents = [BasisMatroid(to_sage(unpack(record, validate=False))) for record in records]
buckets = collections.defaultdict(list)
for i, parent in enumerate(parents):
    buckets[parent._bases_invariant()].append(i)
aligned = [[] for _ in parents]
for line in (args.directory/f"representations-r4-n{n}.jsonl").read_text().splitlines():
    raw = json.loads(line)["matrix"]
    bm = BasisMatroid(Matroid(matrix=matrix(GF(5), raw)))
    for i in buckets[bm._bases_invariant()]:
        isomorphic, mapping = bm.is_isomorphic(parents[i], certificate=True)
        if isomorphic:
            aligned[i].append(permute(raw, [int(mapping[j]) for j in range(n)]))
            break
    else:
        raise AssertionError("represented class missing from abstract catalogue")
temporary = output.with_suffix(".tmp")
total = 0
with temporary.open("x") as stream:
    for i, (parent, matrices, record) in enumerate(zip(parents, aligned, records)):
        basis = sorted(map(int,parent.basis()))
        generators = automorphisms(parent)
        labelled = representation_orbit(matrices, basis, generators)
        for a in labelled:
            candidate = Matroid(matrix=matrix(GF(5), a))
            assert candidate.equals(parent)
        total += len(labelled)
        stream.write(json.dumps({"index": i, "matroid": record, "matrices": labelled,
                                 "connected": bool(parent.is_connected()),
                                 "unlabelled_classes": len(matrices)})+"\n")
        if i % 100 == 0:
            print(json.dumps({"size":n,"parents":i+1,"total":len(parents),
                              "labelled_representations":total,"seconds":monotonic()-started}),flush=True)
temporary.replace(output)
summary = {"size":n,"abstract_classes":len(parents),"labelled_representations":total,
           "seconds":monotonic()-started,"complete":True,
           "method":"all field classes, alignment by isomorphism, full automorphism-group orbits"}
output.with_suffix(".summary.json").write_text(json.dumps(summary,indent=2)+"\n")
print(json.dumps(summary),flush=True)
