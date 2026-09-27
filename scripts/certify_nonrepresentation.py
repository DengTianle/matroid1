"""Independent determinant SAT encoding and checked DRAT for each candidate."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from gf5minors.compact import unpack
from gf5minors.representation import represent

parser = argparse.ArgumentParser()
parser.add_argument("input", type=Path)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--seconds", type=float, default=60)
parser.add_argument("--start", type=int, default=0)
parser.add_argument("--stop", type=int)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
records = [json.loads(line) for line in args.input.read_text().splitlines()]
stop = min(args.stop or len(records), len(records))
started = monotonic()
verified = 0
unknown = []
with (args.output/"verification.jsonl").open("x") as log:
    for index in range(args.start, stop):
        record = records[index]
        m = unpack(record)
        directory = args.output/f"matroid-{index:04d}"
        result = represent(m, seconds=args.seconds, artifact_dir=directory)
        if result.status == "SAT":
            raise AssertionError(("Representable alleged excluded minor", index))
        if result.status == "UNSAT":
            assert result.proof_written
            checked = subprocess.run([str(ROOT/"vendor/drat-trim/drat-trim"),
                                      str(directory/"representation.cnf"),str(directory/"proof.drat"),
                                      "-t", str(int(args.seconds))],
                                     text=True, capture_output=True, timeout=args.seconds+10)
            (directory/"drat-check.txt").write_text(checked.stdout+checked.stderr)
            result.proof_checked = any(line.strip() == "s VERIFIED" for line in checked.stdout.splitlines())
            assert result.proof_checked, (index, checked.returncode, checked.stdout[-1000:])
            verified += 1
        else:
            unknown.append(index)
        report = {"index":index,"matroid_id":m.labelled_id(),**result.to_record()}
        (directory/"result.json").write_text(json.dumps(report, indent=2)+"\n")
        log.write(json.dumps(report)+"\n")
        log.flush()
        print(json.dumps({"index":index,"status":result.status,"proof_checked":result.proof_checked,
                          "seconds":result.seconds}), flush=True)
summary = {"input_sha256":sha256(args.input.read_bytes()).hexdigest(),"start":args.start,"stop":stop,
           "verified":verified,"unknown":unknown,"complete":not unknown,
           "seconds":monotonic()-started}
(args.output/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
print(json.dumps(summary),flush=True)
