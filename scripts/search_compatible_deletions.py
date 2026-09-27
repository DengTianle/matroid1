"""Exhaustive deletion-compatible extensions, followed by contraction checks.

For target n>=9, all deletion matroids force the matroid basis axioms.
For n<=8, explicit basis axioms are supplied as extra clauses.
"""
import argparse
import collections
from functools import lru_cache
from hashlib import sha256
from itertools import combinations
import json
from pathlib import Path
import subprocess
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sage.all import Matroid
from sage.matroids.advanced import BasisMatroid
from gf5minors.compact import unpack,pack_sage
from gf5minors.projective import permute,extension_patterns
from gf5minors.sage_bridge import to_sage
from gf5minors.provenance import manifest


def sage_record(record):
    return BasisMatroid(to_sage(unpack(record,validate=False)))


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


class Catalogue:
    def __init__(self, records, labelled=False):
        self.records = records
        self.matroids = [sage_record(record["matroid"] if labelled else record) for record in records]
        self.buckets = collections.defaultdict(list)
        for i,m in enumerate(self.matroids):
            self.buckets[m._bases_invariant()].append(i)

    def match(self,m,certificate=False):
        m = BasisMatroid(m)
        for i in self.buckets[m._bases_invariant()]:
            answer = self.matroids[i].is_isomorphic(m,certificate=certificate)
            if certificate:
                if answer[0]:
                    return i,answer[1]
            elif answer:
                return i
        return None


def extension_coordinates(parent):
    triples = list(combinations(range(parent.size()),3))
    groups = {}
    coordinates = []
    for triple in triples:
        if parent.rank(triple) < 3:
            coordinates.append(0)
        else:
            flat = frozenset(parent.closure(triple))
            if flat not in groups:
                groups[flat] = len(groups)+1
            coordinates.append(groups[flat])
    return triples,coordinates


def project_table(triple_coordinates,patterns):
    positions = {}
    for i,coordinate in enumerate(triple_coordinates):
        if coordinate:
            positions.setdefault(coordinate,i)
    coordinates = sorted(positions)
    result = set()
    for pattern in patterns:
        for i,coordinate in enumerate(triple_coordinates):
            if coordinate == 0:
                assert not (pattern >> i & 1)
            else:
                assert (pattern >> i & 1) == (pattern >> positions[coordinate] & 1)
        result.add(sum((pattern >> positions[v] & 1) << j for j,v in enumerate(coordinates)))
    return {"coordinates":coordinates,"patterns":sorted(result)}


parser = argparse.ArgumentParser()
parser.add_argument("--size",type=int,required=True)
parser.add_argument("--parents",type=Path,default=ROOT/"data/parents")
parser.add_argument("--rank3",type=Path,default=ROOT/"data/parents-r3")
parser.add_argument("--output",type=Path,required=True)
parser.add_argument("--start",type=int,default=0)
parser.add_argument("--stop",type=int)
parser.add_argument("--seconds",type=float,default=1000)
parser.add_argument("--per-parent",type=float,default=60)
parser.add_argument("--method",choices=("sat","join","both"),default="sat")
args = parser.parse_args()
n = args.size
assert 7 <= n <= 11
args.output.mkdir(parents=True,exist_ok=False)
manifest(ROOT,args.output,vars(args),
         [args.parents/f"labelled-r4-n{k}.jsonl" for k in (n-2,n-1)]+
         [args.rank3/f"abstract-r3-n{k}.jsonl" for k in range(4,n)])
started = monotonic()
parents = read_jsonl(args.parents/f"labelled-r4-n{n-1}.jsonl")
minor_catalogue = Catalogue(read_jsonl(args.parents/f"labelled-r4-n{n-2}.jsonl"),labelled=True)
rank3 = {}
for k in range(4,n):
    rank3[k] = Catalogue(read_jsonl(args.rank3/f"abstract-r3-n{k}.jsonl"))
worker = subprocess.Popen(["/home/t/tianle51/miniconda3/envs/matroid1/bin/python",str(ROOT/"scripts/table_worker.py")],
                          stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True,bufsize=1)
found = collections.defaultdict(list)
unknown = []
total_candidates = 0
total_found = 0
stop = min(args.stop or len(parents),len(parents))
completed = []

@lru_cache(maxsize=10000)
def minor_patterns(bits,n_minor):
    record = {"schema":"gf5-bits-v1","n":n_minor,"rank":4,"bits":bits}
    minor = sage_record(record)
    match = minor_catalogue.match(minor,certificate=True)
    if match is None:
        raise AssertionError("deletion of represented parent absent from complete catalogue")
    index,mapping = match
    aligned = [permute(matrix,[int(mapping[j]) for j in range(n_minor)])
               for matrix in minor_catalogue.records[index]["matrices"]]
    return extension_patterns(aligned)

def candidate_record(parent_record,triples,coordinates,pattern):
    original_bits = int(parent_record["bits"],16)
    old_indices = {subset:i for i,subset in enumerate(combinations(range(n-1),4))}
    triple_map = dict(zip(triples,coordinates))
    bits = 0
    for i,subset in enumerate(combinations(range(n),4)):
        if subset[-1] == n-1:
            coordinate = triple_map[subset[:-1]]
            value = coordinate and (pattern >> (coordinate-1) & 1)
        else:
            value = original_bits >> old_indices[subset] & 1
        if value:
            bits |= 1 << i
    return {"schema":"gf5-bits-v1","n":n,"rank":4,"bits":format(bits,"x")}

def small_basis_clauses(parent_record,triples,coordinates):
    # Translate the ordered basis axiom to the hyperplane variables/constants.
    old_bits = int(parent_record["bits"],16)
    old_indices = {subset:i for i,subset in enumerate(combinations(range(n-1),4))}
    triple_map = dict(zip(triples,coordinates))
    variables = {}
    subsets = list(map(frozenset,combinations(range(n),4)))
    for subset in subsets:
        ordered = tuple(sorted(subset))
        if n-1 in subset:
            variables[subset] = triple_map[ordered[:-1]] or False
        else:
            variables[subset] = bool(old_bits >> old_indices[ordered] & 1)
    clauses = []
    def clause(terms):
        literals = []
        for sign,variable in terms:
            if type(variable) is bool:
                if variable == (sign > 0):
                    return
            else:
                literals.append(sign*variable)
        if not any(-v in literals for v in literals):
            clauses.append(sorted(set(literals)))
    for a in subsets:
        for b in subsets:
            if len(a-b) < 2:
                continue
            for e in a-b:
                clause([(-1,variables[a]),(-1,variables[b])]+[(1,variables[(a-{e})|{f}]) for f in b-a])
    return clauses

with (args.output/"parents.jsonl").open("x") as log, (args.output/"candidates.jsonl").open("x") as candidates_file, (args.output/"excluded.jsonl").open("x") as excluded_file:
    try:
        for index in range(args.start,stop):
            if monotonic()-started > args.seconds:
                break
            entry = parents[index]
            if not entry["connected"]:
                completed.append(index)
                log.write(json.dumps({"parent":index,"status":"DISCONNECTED_PARENT"})+"\n")
                continue
            parent_started = monotonic()
            parent = sage_record(entry["matroid"])
            triples,coordinates = extension_coordinates(parent)
            triple_map = dict(zip(triples,coordinates))
            represented = project_table(coordinates,extension_patterns(entry["matrices"]))
            assert represented["coordinates"] == list(range(1,max(coordinates)+1))
            tables = []
            for f in range(n-1):
                minor = parent.delete(f)
                record = pack_sage(minor)
                patterns = minor_patterns(record["bits"],n-2)
                remaining = [j for j in range(n-1) if j != f]
                minor_coordinates = [triple_map[triple] for triple in combinations(remaining,3)]
                tables.append(project_table(minor_coordinates,patterns))
            problem = {"variables":max(coordinates),"represented":represented["patterns"],"tables":tables,
                       "seconds":args.per_parent,"method":args.method}
            if n <= 8:
                problem["clauses"] = small_basis_clauses(entry["matroid"],triples,coordinates)
            worker.stdin.write(json.dumps(problem)+"\n")
            worker.stdin.flush()
            result = json.loads(worker.stdout.readline())
            if "error" in result:
                raise RuntimeError(result)
            result["problem_sha256"] = sha256(json.dumps(
                {key:value for key,value in problem.items() if key not in ("seconds","method")},
                sort_keys=True,separators=(",",":")).encode()).hexdigest()
            result["models_sha256"] = sha256(json.dumps(sorted(result["models"])).encode()).hexdigest()
            result["models_count"] = len(result["models"])
            if result["status"] != "EXHAUSTED":
                unknown.append(index)
                (args.output/f"unresolved-{index}.json").write_text(json.dumps(problem))
            for pattern in result["models"]:
                record = candidate_record(entry["matroid"],triples,coordinates,pattern)
                m = sage_record(record)
                assert m.is_valid() and m.is_simple()
                assert m.delete(n-1).equals(parent)
                total_candidates += 1
                record["parent_index"] = index
                candidates_file.write(json.dumps(record)+"\n")
                excluded = True
                for e in range(n):
                    contraction = m.contract(e).simplify()
                    if contraction.size() > 3 and rank3[contraction.size()].match(contraction) is None:
                        excluded = False
                        break
                if not excluded:
                    continue
                assert m.is_3connected()
                bucket = found[m._bases_invariant()]
                if any(m.is_isomorphic(previous) for previous in bucket):
                    continue
                bucket.append(m)
                excluded_file.write(json.dumps(record)+"\n")
                excluded_file.flush()
                total_found += 1
            completed.append(index)
            result.pop("models")
            result.update({"parent":index,"candidates_total":total_candidates,"excluded_classes":total_found,
                           "wall_seconds":monotonic()-parent_started})
            log.write(json.dumps(result)+"\n")
            log.flush()
            if index % 25 == 0:
                print(json.dumps(result),flush=True)
    finally:
        worker.stdin.close()
        worker.wait(timeout=10)
summary = {"target_size":n,"target_rank":4,"start":args.start,"stop":stop,"parents_total":len(parents),
           "completed_parents":len(completed),"last_completed":completed[-1] if completed else None,
           "unknown_parents":unknown,"deletion_minimal_candidates":total_candidates,
           "excluded_classes_within_run":total_found,"seconds":monotonic()-started,
           "complete_for_range":len(completed)==stop-args.start and not unknown,
           "global_complete":args.start==0 and stop==len(parents) and len(completed)==stop and not unknown}
(args.output/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
print(json.dumps(summary),flush=True)
