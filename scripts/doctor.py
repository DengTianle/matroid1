"""Read-only environment inventory; no installation or solver search."""
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import sys


def main():
    packages = {}
    for name in ("python-sat", "numpy", "sagemath-standard", "pytest"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    sage_meta = []
    for path in sorted(Path("/home/t/tianle51/miniconda3/envs/my-sage/conda-meta").glob("*sage*.json")):
        record = json.loads(path.read_text())
        sage_meta.append({k: record.get(k) for k in ("name", "version", "build")})
    print(json.dumps({
        "python": sys.version, "executable": sys.executable,
        "host": platform.node(), "platform": platform.platform(),
        "slurm": {key: value for key, value in os.environ.items()
                  if key in ("SLURM_JOB_ID", "SLURM_JOB_CPUS_PER_NODE", "SLURM_CPUS_PER_TASK", "SLURM_JOB_PARTITION")},
        "packages": packages, "sage_conda": sage_meta,
        "tools": {name: shutil.which(name) for name in ("sbatch", "srun", "sage", "drat-trim", "gcc")},
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
