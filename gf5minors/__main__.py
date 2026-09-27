"""Bounded commands; no command launches an unbounded global search."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import sys

from .matroid import BasisMatroid, fano, vamos, uniform, rank4_fixture
from .representation import represent, check_excluded
from .extensions import enumerate_extensions


def source_hash():
    digest = sha256()
    for path in sorted(Path(__file__).parent.glob("*.py")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def provenance():
    return {"utc": datetime.now(timezone.utc).isoformat(), "python": sys.version,
            "python_sat": importlib.metadata.version("python-sat"),
            "host": platform.node(), "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
            "source_sha256": source_hash()}


def atomic_json(path, data):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def load(path):
    return BasisMatroid.from_record(json.loads(Path(path).read_text()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    fixtures = commands.add_parser("fixtures")
    fixtures.add_argument("--output", required=True, type=Path)
    for name in ("represent", "excluded"):
        sub = commands.add_parser(name)
        sub.add_argument("input", type=Path)
        sub.add_argument("--output", required=True, type=Path)
        sub.add_argument("--seconds", type=float, default=30,
                         help="per recognition call (excluded may make 1+2n calls)")
    extend = commands.add_parser("extend")
    extend.add_argument("input", type=Path)
    extend.add_argument("--output", required=True, type=Path)
    extend.add_argument("--seconds", type=float, default=30)
    extend.add_argument("--max-models", type=int, default=100)
    extend.add_argument("--simple", action="store_true")
    extend.add_argument("--cosimple", action="store_true")
    extend.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.command == "fixtures":
        args.output.mkdir(parents=True, exist_ok=False)
        for name, matroid in {"U2_6": uniform(2, 6), "U2_7": uniform(2, 7),
                               "F7": fano(), "V8": vamos(), "rank4_11_representable": rank4_fixture()}.items():
            atomic_json(args.output / f"{name}.json", matroid.to_record())
        return
    if args.seconds <= 0:
        parser.error("--seconds must be positive")
    matroid = load(args.input)
    if args.command == "extend":
        if args.max_models < 1:
            parser.error("--max-models must be positive")
        identity = {"schema": "gf5-extension-run-v1", "parent": matroid.to_record(),
                    "simple": args.simple, "cosimple": args.cosimple,
                    "source_sha256": source_hash()}
        journal = args.output / "extensions.jsonl"
        previous = []
        if args.resume:
            if json.loads((args.output / "identity.json").read_text()) != identity:
                parser.error("resume identity differs (parent, filters, or code changed)")
            # A truncated final record fails loudly; do not silently claim coverage.
            previous = [BasisMatroid.from_record(json.loads(line)) for line in journal.read_text().splitlines()]
        else:
            args.output.mkdir(parents=True, exist_ok=False)
            atomic_json(args.output / "identity.json", identity)
        atomic_json(args.output / "run.json", {"status": "RUNNING", "provenance": provenance()})
        with journal.open("a" if args.resume else "x") as stream:
            def emit(value):
                stream.write(json.dumps(value.to_record(), sort_keys=True) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            report = enumerate_extensions(matroid, emit, simple=args.simple, cosimple=args.cosimple,
                                          seconds=args.seconds, max_models=args.max_models, previous=previous)
        report["provenance"] = provenance()
        atomic_json(args.output / "run.json", report)
    else:
        function = represent if args.command == "represent" else check_excluded
        report = function(matroid, seconds=args.seconds, artifact_dir=args.output)
        if args.command == "represent":
            report = report.to_record()
        atomic_json(args.output / "provenance.json", provenance())
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
