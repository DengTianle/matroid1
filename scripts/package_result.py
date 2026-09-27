"""Package the verified result and its exact computational inputs, without caches."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("directory", type=Path)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
directory = args.directory.resolve()
output = args.output.resolve()
assert not output.is_relative_to(directory), "Archive must be outside the directory it packages"
verification = json.loads((directory/"verification.json").read_text())
assert verification["search_complete"]
assert verification["all_nonrepresentation_proofs_checked"]
assert verification["all_immediate_minor_matrices_checked"]
summary = json.loads((directory/"summary.json").read_text())
assert sha256((directory/"excluded.jsonl").read_bytes()).hexdigest() == verification["catalogue_sha256"]
for relative,digest in summary["critical_sources"].items():
    assert sha256((ROOT/relative).read_bytes()).hexdigest() == digest, ("Source changed",relative)
paths = [directory, ROOT/"README.md", ROOT/"pyproject.toml", ROOT/"docs", ROOT/"data/parents",
         ROOT/"data/parents-r3", ROOT/"data/catalogue",ROOT/"data/known_counts.json",ROOT/"data/reference_manifest.json"]
for folder in ("gf5minors","scripts","tests","slurm"):
    paths.extend(path for path in (ROOT/folder).glob("*") if path.suffix in (".py",".slurm"))
for filename in ("drat-trim.c","LICENSE","README.md","manifest.json"):
    paths.append(ROOT/"vendor/drat-trim"/filename)
paths.extend(ROOT/shard["directory"] for shard in summary["shards"])
paths.extend(ROOT/f"runs/calibration-n{n}" for n in range(7,11))
paths.extend(ROOT/name for name in ("runs/calibration-n9-both","runs/calibration-n10-join"))
with tarfile.open(output,"x:gz",compresslevel=6) as archive:
    for path in paths:
        archive.add(path,arcname=str(path.relative_to(ROOT)))
report = {"archive":str(output.relative_to(ROOT)),"bytes":output.stat().st_size,
          "sha256":sha256(output.read_bytes()).hexdigest(),"excluded_classes":verification["excluded_classes"],
          "catalogue_sha256":verification["catalogue_sha256"]}
output.with_suffix(output.suffix+".json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report),flush=True)
