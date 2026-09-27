"""Complete represented simple rank-r catalogue by linear extensions.

Keep every projective representation class, not just every abstract matroid.
The full level files are published only after the level is exhausted.
"""
import argparse
import collections
import json
from pathlib import Path
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sage.all import GF, Matroid, identity_matrix, matrix
from sage.matroids.advanced import BasisMatroid
from gf5minors.compact import pack_sage


def representation_record(m):
    vectors = m.representation_vectors()
    return {"matrix": [[int(vectors[j][i]) for j in range(m.size())] for i in range(m.full_rank())]}


def read_level(path):
    return [Matroid(matrix=matrix(GF(5), json.loads(line)["matrix"])) for line in path.read_text().splitlines()]


parser = argparse.ArgumentParser()
parser.add_argument("--rank", type=int, default=4)
parser.add_argument("--max-size", type=int, default=9)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--seconds", type=float, default=1000)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
started = monotonic()
parents = [Matroid(matrix=identity_matrix(GF(5), args.rank))]
for n in range(args.rank + 1, args.max_size + 1):
    output = args.output / f"representations-r{args.rank}-n{n}.jsonl"
    if output.exists():
        parents = read_level(output)
        print("loaded", n, len(parents), flush=True)
        continue
    by_invariant = collections.defaultdict(list)
    attempts = 0
    level_started = monotonic()
    new_parents = []
    for index, parent in enumerate(parents):
        if monotonic() - started > args.seconds:
            print(json.dumps({"status": "TIME_LIMIT", "size": n, "finished_parents": index,
                              "parents": len(parents), "attempts": attempts,
                              "new_representation_classes": len(new_parents)}), flush=True)
            sys.exit(3)
        for candidate in parent.linear_extensions(element=n-1, simple=True):
            attempts += 1
            abstract = BasisMatroid(candidate)
            invariant = abstract._bases_invariant()
            bucket = by_invariant[invariant]
            if any(candidate.is_field_isomorphic(previous) for previous in bucket):
                continue
            bucket.append(candidate)
            new_parents.append(candidate)
        if index % 100 == 0:
            print(json.dumps({"size": n, "finished_parents": index+1, "parents": len(parents),
                              "attempts": attempts, "representation_classes": len(new_parents),
                              "seconds": monotonic()-level_started}), flush=True)
    temporary = output.with_suffix(".tmp")
    temporary.write_text("".join(json.dumps(representation_record(m)) + "\n" for m in new_parents))
    temporary.replace(output)
    # Abstract parent deduplication is safe after represented generation finishes.
    abstract_buckets = collections.defaultdict(list)
    abstracts = []
    for m in new_parents:
        bm = BasisMatroid(m)
        bucket = abstract_buckets[bm._bases_invariant()]
        if any(bm.is_isomorphic(old) for old in bucket):
            continue
        bucket.append(bm)
        abstracts.append(bm)
    abstract_path = args.output / f"abstract-r{args.rank}-n{n}.jsonl"
    abstract_path.write_text("".join(json.dumps(pack_sage(m)) + "\n" for m in abstracts))
    summary = {"rank": args.rank, "size": n, "representation_classes": len(new_parents),
               "abstract_classes": len(abstracts), "attempts": attempts,
               "seconds": monotonic()-level_started, "complete": True,
               "method": "linear extensions retaining all field-isomorphism classes"}
    output.with_suffix(".summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary), flush=True)
    parents = new_parents
