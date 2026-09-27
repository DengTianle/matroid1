"""Portable lexicographic basis-bit records for larger catalogues."""
from itertools import combinations
from .matroid import BasisMatroid


def pack(matroid):
    bits = sum(1 << i for i, b in enumerate(combinations(range(matroid.n), matroid.r))
               if frozenset(b) in matroid.bases)
    return {"schema": "gf5-bits-v1", "n": matroid.n, "rank": matroid.r, "bits": format(bits, "x")}


def unpack(record, validate=True):
    if record.get("schema") == "gf5-bases-v1":
        return BasisMatroid.from_record(record)
    if record.get("schema") != "gf5-bits-v1":
        raise ValueError("unrecognized matroid encoding")
    n, r = record["n"], record["rank"]
    subsets = list(combinations(range(n), r))
    bits = int(record["bits"], 16)
    if bits < 0 or bits >> len(subsets):
        raise ValueError("bit vector exceeds ground set")
    m = BasisMatroid(n, r, frozenset(frozenset(b) for i, b in enumerate(subsets) if bits >> i & 1))
    return m.validate() if validate else m


def pack_sage(matroid):
    ground = sorted(matroid.groundset())
    r = int(matroid.full_rank())
    bits = sum(1 << i for i, b in enumerate(combinations(ground, r)) if matroid.is_independent(b))
    return {"schema": "gf5-bits-v1", "n": len(ground), "rank": r, "bits": format(bits, "x")}
