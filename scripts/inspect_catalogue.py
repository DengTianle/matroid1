"""Inspect Sage's inert catalogue serialization and installed small-matroid APIs."""
from pathlib import Path
import json
import pickletools
import zlib
import sys

ROOT = Path(__file__).resolve().parents[1]
raw = (ROOT / "data/raw/brettell/gf5_excluded_minors10.sobj").read_bytes()
data = zlib.decompress(raw)
globals_seen = set()
first = []
for i, (op, arg, position) in enumerate(pickletools.genops(data)):
    if op.name == "GLOBAL":
        globals_seen.add(arg)
    if i < 70:
        first.append([position, op.name, str(arg)[:300]])
print(json.dumps({"bytes_decompressed": len(data), "globals": sorted(globals_seen), "first_ops": first}, indent=2), flush=True)
from sage.all import *
from sage.env import SAGE_VERSION
print("Sage version", SAGE_VERSION, flush=True)
m = matroids.Uniform(2, 5)
print("BasisMatroid API", [name for name in dir(m) if any(s in name for s in ("extension", "splice", "canonical", "isomorph", "flat"))], flush=True)
m = Matroid(matrix=matrix(GF(5), [[1,0,0,0,1], [0,1,0,0,1], [0,0,1,0,1], [0,0,0,1,1]]))
print("Linear API", [name for name in dir(m) if any(s in name for s in ("extension", "isomorph", "representation", "equiv"))], flush=True)
for name in ("linear_extensions", "linear_extension", "extensions", "is_isomorphic", "is_field_isomorphic", "representation"):
    method = getattr(m, name, None)
    if method is not None:
        print(name, str(method.__doc__)[:5500], flush=True)
