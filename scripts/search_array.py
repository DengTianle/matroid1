"""Divide a complete target-size search into disjoint Slurm array ranges."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--shards", type=int, default=4)
parser.add_argument("--size", type=int, default=11)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--seconds", type=float, default=3300)
args = parser.parse_args()
task = int(os.environ["SLURM_ARRAY_TASK_ID"])
assert 0 <= task < args.shards
parents = ROOT/f"data/parents/labelled-r4-n{args.size-1}.jsonl"
count = sum(1 for line in parents.open() if line.strip())
start = count*task//args.shards
stop = count*(task+1)//args.shards
output = args.output/f"shard-{task:02d}"
print(json.dumps({"task":task,"start":start,"stop":stop,"parents_total":count}),flush=True)
command = [sys.executable,str(ROOT/"scripts/search_compatible_deletions.py"),
           "--size",str(args.size),"--start",str(start),"--stop",str(stop),
           "--method","join","--seconds",str(args.seconds),"--output",str(output)]
subprocess.run(command,check=True)
