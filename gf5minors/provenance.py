"""Small immutable source/input snapshots for computational research runs."""
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import shutil
import sys


def manifest(root, output, arguments, inputs):
    root, output = Path(root), Path(output)
    sources = {}
    for folder in ("gf5minors", "scripts", "slurm"):
        for path in sorted((root/folder).glob("*")):
            if path.suffix not in (".py", ".slurm"):
                continue
            relative = path.relative_to(root)
            sources[str(relative)] = sha256(path.read_bytes()).hexdigest()
            target = output/"source"/relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
    data = {str(Path(path).relative_to(root)):sha256(Path(path).read_bytes()).hexdigest() for path in inputs}
    record = {"created_utc":datetime.now(timezone.utc).isoformat(),"arguments":arguments,
              "python":sys.version,"executable":sys.executable,"platform":platform.platform(),
              "slurm_job_id":os.environ.get("SLURM_JOB_ID"),"slurm_array_task_id":os.environ.get("SLURM_ARRAY_TASK_ID"),
              "sources":sources,"inputs":data}
    (output/"manifest.json").write_text(json.dumps(record, indent=2, default=str)+"\n")
    return record
