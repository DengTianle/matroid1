"""Read completed research journals; no cluster control or computation."""
import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("directory", type=Path)
args = parser.parse_args()
shards = []
for directory in sorted(args.directory.glob("shard-*")):
    manifest = json.loads((directory/"manifest.json").read_text())
    arguments = manifest["arguments"]
    count = unknown = candidates = excluded = 0
    for line in (directory/"parents.jsonl").open():
        if not line.endswith("\n"):
            continue
        entry = json.loads(line)
        count += 1
        unknown += entry["status"] == "UNKNOWN"
        candidates = entry.get("candidates_total",candidates)
        excluded = entry.get("excluded_classes",excluded)
    summary = directory/"summary.json"
    complete = summary.exists() and json.loads(summary.read_text())["complete_for_range"]
    shards.append({"shard":directory.name,"completed":count,"total":arguments["stop"]-arguments["start"],
                   "unknown":unknown,"candidates":candidates,"local_excluded_classes":excluded,"complete":complete})
done = sum(s["completed"] for s in shards)
total = sum(s["total"] for s in shards)
print(json.dumps({"completed":done,"total":total,"percent":round(100*done/total,1),
                  "unknown":sum(s["unknown"] for s in shards),"shards":shards},indent=2))
