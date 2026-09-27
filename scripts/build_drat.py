"""Build the downloaded proof checker locally inside a Slurm allocation."""
from hashlib import sha256
import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]/"vendor/drat-trim"
manifest = json.loads((root/"manifest.json").read_text())
source = root/"drat-trim.c"
assert sha256(source.read_bytes()).hexdigest() == manifest["files"][source.name]["sha256"]
subprocess.run(["gcc", str(source), "-std=c99", "-O2", "-o", str(root/"drat-trim")], check=True)
print(json.dumps({"built":str(root/"drat-trim"), "source_sha256":manifest["files"][source.name]["sha256"],
                  "binary_sha256":sha256((root/"drat-trim").read_bytes()).hexdigest()}))
