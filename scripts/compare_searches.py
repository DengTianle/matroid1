"""Compare full labelled candidate sets from independent exhaustive searches."""
import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("first", type=Path)
parser.add_argument("second", type=Path)
args = parser.parse_args()

def data(directory):
    summary = json.loads((directory/"summary.json").read_text())
    assert summary["global_complete"]
    records = [json.loads(line) for line in (directory/"candidates.jsonl").read_text().splitlines()]
    keys = [(r["parent_index"],r["bits"]) for r in records]
    assert len(keys) == len(set(keys))
    return summary,set(keys)

first,a = data(args.first)
second,b = data(args.second)
assert a == b, (len(a-b),len(b-a))
report = {"first":str(args.first),"second":str(args.second),"size":first["target_size"],
          "rank":first["target_rank"],"labelled_candidates":len(a),"exact_match":True}
(args.second/"independent-comparison.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report))
