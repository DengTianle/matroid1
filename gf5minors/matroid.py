"""Labelled basis families and independent finite-field linear algebra."""
from dataclasses import dataclass
from hashlib import sha256
from itertools import combinations
import json


def rank_mod(matrix, p=5):
    """Gaussian rank over a prime field, without floating point arithmetic."""
    a = [[int(x) % p for x in row] for row in matrix]
    if not a:
        return 0
    if any(len(row) != len(a[0]) for row in a):
        raise ValueError("ragged matrix")
    k = 0
    for j in range(len(a[0])):
        pivot = next((i for i in range(k, len(a)) if a[i][j]), None)
        if pivot is None:
            continue
        a[k], a[pivot] = a[pivot], a[k]
        inverse = pow(a[k][j], -1, p)
        a[k] = [(x * inverse) % p for x in a[k]]
        for i in range(k + 1, len(a)):
            factor = a[i][j]
            a[i] = [(x - factor * y) % p for x, y in zip(a[i], a[k])]
        k += 1
        if k == len(a):
            break
    return k


@dataclass(frozen=True)
class BasisMatroid:
    n: int
    r: int
    bases: frozenset

    def __post_init__(self):
        if type(self.n) is not int or type(self.r) is not int or not 0 <= self.r <= self.n:
            raise ValueError("require integer 0 <= rank <= size")
        bases = frozenset(frozenset(b) for b in self.bases)
        if not bases or any(len(b) != self.r or any(type(e) is not int or not 0 <= e < self.n for e in b) for b in bases):
            raise ValueError("invalid basis family shape")
        object.__setattr__(self, "bases", bases)

    def validate(self):
        """Check all ordered instances of the basis-exchange axiom."""
        for a in self.bases:
            for b in self.bases:
                for x in a - b:
                    if not any((a - {x}) | {y} in self.bases for y in b - a):
                        raise ValueError(f"basis exchange fails at {sorted(a)}, {sorted(b)}, {x}")
        return self

    def rank(self, subset):
        subset = frozenset(subset)
        if not subset <= frozenset(range(self.n)):
            raise ValueError("element outside ground set")
        return max(len(b & subset) for b in self.bases)

    def minor(self, e, operation):
        if type(e) is not int or not 0 <= e < self.n:
            raise ValueError("element outside ground set")
        if operation == "delete":
            projected = [b - {e} for b in self.bases]
        elif operation == "contract":
            containing = [b for b in self.bases if e in b]
            projected = [b - {e} for b in containing or self.bases]
        else:
            raise ValueError("operation must be delete or contract")
        r = max(map(len, projected))
        # Preserve the remaining labels in increasing order, then renumber.
        return BasisMatroid(self.n - 1, r, frozenset(
            frozenset(x - (x > e) for x in b) for b in projected if len(b) == r))

    def dual(self):
        ground = frozenset(range(self.n))
        return BasisMatroid(self.n, self.n - self.r, frozenset(ground - b for b in self.bases))

    def relabel(self, permutation):
        if sorted(permutation) != list(range(self.n)):
            raise ValueError("expected a permutation of the ground set")
        return BasisMatroid(self.n, self.r, frozenset(
            frozenset(permutation[e] for e in b) for b in self.bases))

    def is_simple(self):
        return all(self.rank(s) == len(s) for k in (1, 2)
                   for s in combinations(range(self.n), k))

    def to_record(self):
        return {"schema": "gf5-bases-v1", "n": self.n, "rank": self.r,
                "bases": sorted([sorted(b) for b in self.bases])}

    @classmethod
    def from_record(cls, record):
        if record.get("schema") != "gf5-bases-v1":
            raise ValueError("unsupported matroid record schema")
        bases = record["bases"]
        if any(len(set(b)) != len(b) for b in bases) or len({tuple(sorted(b)) for b in bases}) != len(bases):
            raise ValueError("duplicate elements or bases in record")
        return cls(record["n"], record["rank"], frozenset(frozenset(b) for b in bases)).validate()

    def labelled_id(self):
        """Stable file identifier, explicitly NOT an isomorphism invariant."""
        data = json.dumps(self.to_record(), sort_keys=True, separators=(",", ":"))
        return sha256(data.encode()).hexdigest()


def uniform(r, n):
    return BasisMatroid(n, r, frozenset(frozenset(b) for b in combinations(range(n), r)))


def from_matrix(matrix, p=5, n=None):
    if n is None:
        n = len(matrix[0]) if matrix else 0
    if any(len(row) != n for row in matrix):
        raise ValueError("matrix width disagrees with size")
    r = rank_mod(matrix, p)
    return BasisMatroid(n, r, frozenset(
        frozenset(b) for b in combinations(range(n), r)
        if rank_mod([[row[j] for j in b] for row in matrix], p) == r))


def verify_representation(matroid, matrix):
    """Independently check rank and EVERY maximal minor of a GF(5) witness."""
    return (len(matrix) == matroid.r and all(len(row) == matroid.n for row in matrix)
            and all(type(x) is int and 0 <= x < 5 for row in matrix for x in row)
            and from_matrix(matrix, n=matroid.n) == matroid)


def fano():
    return from_matrix([[1, 0, 0, 1, 1, 0, 1],
                        [0, 1, 0, 1, 0, 1, 1],
                        [0, 0, 1, 0, 1, 1, 1]], p=2)


def vamos():
    forbidden = {frozenset(b) for b in ((0, 1, 2, 3), (0, 1, 4, 5),
                                      (0, 1, 6, 7), (2, 3, 4, 5), (2, 3, 6, 7))}
    return BasisMatroid(8, 4, uniform(4, 8).bases - forbidden)


def rank4_fixture():
    """A deterministic represented 11-element fixture, not a search result."""
    return from_matrix([[1, 0, 0, 0, 1, 1, 1, 1, 1, 0, 2],
                        [0, 1, 0, 0, 1, 2, 3, 4, 0, 1, 1],
                        [0, 0, 1, 0, 1, 3, 4, 2, 1, 2, 3],
                        [0, 0, 0, 1, 1, 4, 2, 3, 2, 3, 1]])
