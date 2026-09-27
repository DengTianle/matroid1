"""Exact GF(5) representability by a normalized matrix and determinant CNF.

The SAT compiler and the Gaussian witness checker use separate algorithms.
An UNSAT answer is a solver result, not an independently checked proof.
"""
from dataclasses import dataclass, asdict
from functools import lru_cache
from itertools import combinations
from pathlib import Path
from threading import Timer
from time import monotonic
import json

from .matroid import verify_representation


class FieldCircuit:
    """Constants are ints mod 5; variable expressions are five indicator lits.

    A zero literal is an impossible value, never DIMACS literal zero.
    """
    def __init__(self):
        self.nv = 0
        self.clauses = []
        self.cache = {}

    def variable(self, domain=range(5)):
        domain = tuple(sorted(set(domain)))
        if not domain or any(x not in range(5) for x in domain):
            raise ValueError("bad field domain")
        if len(domain) == 1:
            return domain[0]
        indicators = [0] * 5
        for x in domain:
            self.nv += 1
            indicators[x] = self.nv
        lits = [x for x in indicators if x]
        self.clauses.append(lits)
        self.clauses.extend([-a, -b] for a, b in combinations(lits, 2))
        return tuple(indicators)

    @staticmethod
    def remap(expression, function):
        if isinstance(expression, int):
            return function(expression) % 5
        output = [0] * 5
        for value, literal in enumerate(expression):
            if literal:
                output[function(value) % 5] = literal
        return tuple(output)

    def operation(self, op, a, b):
        if op not in ("add", "mul"):
            raise ValueError("unknown field operation")
        if isinstance(b, int):
            a, b = b, a
        if isinstance(a, int):
            if op == "mul" and a == 0:
                return 0
            return self.remap(b, (lambda x: a + x) if op == "add" else (lambda x: a * x))
        key = (op, a, b)
        if key not in self.cache:
            output = self.variable()
            for x, lx in enumerate(a):
                for y, ly in enumerate(b):
                    if lx and ly:
                        z = (x + y if op == "add" else x * y) % 5
                        self.clauses.append([-lx, -ly, output[z]])
            self.cache[key] = output
        return self.cache[key]

    def require(self, expression, nonzero):
        if isinstance(expression, int):
            if bool(expression) != nonzero:
                self.clauses.append([])
        elif nonzero:
            if expression[0]:
                self.clauses.append([-expression[0]])
        else:
            self.clauses.append([expression[0]] if expression[0] else [])


def encode_representation(matroid, normalize=True):
    matroid.validate()
    # A sparser fundamental support reduces the number of free entries.
    def basis_key(b):
        support = sum((b - {i}) | {j} in matroid.bases
                      for i in b for j in range(matroid.n) if j not in b)
        return support, tuple(sorted(b))
    basis = tuple(sorted(min(matroid.bases, key=basis_key)))
    outside = tuple(e for e in range(matroid.n) if e not in basis)
    bset = frozenset(basis)
    support = [(i, j) for i, e in enumerate(basis) for j, f in enumerate(outside)
               if (bset - {e}) | {f} in matroid.bases]
    # Row/column scalings make every edge of a spanning forest equal to 1.
    parents = list(range(matroid.n))

    def root(x):
        while parents[x] != x:
            parents[x] = parents[parents[x]]
            x = parents[x]
        return x

    forest = set()
    if normalize:
        for i, j in support:
            a, b = root(i), root(matroid.r + j)
            if a != b:
                parents[a] = b
                forest.add((i, j))
    circuit = FieldCircuit()
    block = [[0 for _ in outside] for _ in basis]
    for i, j in support:
        block[i][j] = 1 if (i, j) in forest else circuit.variable(range(1, 5))

    @lru_cache(maxsize=None)
    def determinant(rows, columns):
        if not rows:
            return 1
        value = 0
        for k, j in enumerate(columns):
            entry = block[rows[0]][j]
            if entry == 0:
                continue
            sub = determinant(rows[1:], columns[:k] + columns[k + 1:])
            term = circuit.operation("mul", entry, sub)
            if k % 2:
                term = circuit.operation("mul", 4, term)
            value = circuit.operation("add", value, term)
        return value

    for subset in combinations(range(matroid.n), matroid.r):
        subset = frozenset(subset)
        rows = tuple(i for i, e in enumerate(basis) if e not in subset)
        columns = tuple(j for j, e in enumerate(outside) if e in subset)
        # The complementary minor differs from the full determinant by a sign.
        circuit.require(determinant(rows, columns), subset in matroid.bases)
    matrix = [[0] * matroid.n for _ in basis]
    for i, e in enumerate(basis):
        matrix[i][e] = 1
    for i in range(matroid.r):
        for j, e in enumerate(outside):
            matrix[i][e] = block[i][j]
    metadata = {"basis": basis, "outside": outside, "normalized": normalize,
                "forest": sorted(forest), "free_entries": len(support) - len(forest),
                "expression_matrix": matrix}
    return circuit, matrix, metadata


def solve_limited(solver, seconds, conflict_budget=None):
    """Use Glucose's limited API; expiration is UNKNOWN, never UNSAT."""
    if seconds <= 0:
        return None
    solver.clear_interrupt()
    if conflict_budget is not None:
        if conflict_budget <= 0:
            return None
        solver.conf_budget(conflict_budget)
    timer = Timer(seconds, solver.interrupt)
    timer.daemon = True
    timer.start()
    try:
        return solver.solve_limited(expect_interrupt=True)
    finally:
        timer.cancel()
        timer.join()  # Ensure a callback cannot access a deleted solver.
        solver.clear_interrupt()


@dataclass
class RepresentationResult:
    status: str
    seconds: float
    variables: int
    clauses: int
    matrix: list | None = None
    witness_checked: bool = False
    proof_written: bool = False
    proof_checked: bool = False
    solver: str = "glucose4"

    def to_record(self):
        return asdict(self)


def write_cnf(path, variables, clauses):
    with Path(path).open("w") as stream:
        stream.write(f"p cnf {variables} {len(clauses)}\n")
        for clause in clauses:
            stream.write(" ".join(map(str, clause)) + (" " if clause else "") + "0\n")


def represent(matroid, seconds=30, conflict_budget=None, artifact_dir=None, normalize=True):
    from pysat.solvers import Solver
    started = monotonic()
    circuit, expressions, metadata = encode_representation(matroid, normalize=normalize)
    directory = Path(artifact_dir) if artifact_dir is not None else None
    if directory:
        directory.mkdir(parents=True, exist_ok=False)
        (directory / "matroid.json").write_text(json.dumps(matroid.to_record(), indent=2) + "\n")
        (directory / "encoding.json").write_text(json.dumps(metadata, indent=2) + "\n")
        write_cnf(directory / "representation.cnf", circuit.nv, circuit.clauses)
    with Solver(name="g4", bootstrap_with=circuit.clauses, with_proof=directory is not None) as solver:
        answer = solve_limited(solver, seconds - (monotonic() - started), conflict_budget)
        result = RepresentationResult("UNKNOWN" if answer is None else "SAT" if answer else "UNSAT",
                                      monotonic() - started, circuit.nv, len(circuit.clauses))
        if answer:
            model = {literal for literal in solver.get_model() if literal > 0}
            result.matrix = [[expression if isinstance(expression, int)
                              else next(value for value, literal in enumerate(expression) if literal in model)
                              for expression in row] for row in expressions]
            if not verify_representation(matroid, result.matrix):
                raise AssertionError("SAT model failed the independent matrix checker")
            result.witness_checked = True
        elif answer is False and directory:
            proof = solver.get_proof()
            if proof is not None:
                (directory / "proof.drat").write_text("".join(line + "\n" for line in proof))
                result.proof_written = True
        if directory:
            (directory / "result.json").write_text(json.dumps(result.to_record(), indent=2) + "\n")
    return result


def check_excluded(matroid, seconds=30, artifact_dir=None):
    """Check M and all 2n immediate minors; seconds is PER recognition call."""
    directory = Path(artifact_dir) if artifact_dir else None
    if directory:
        directory.mkdir(parents=True, exist_ok=False)
    original = represent(matroid, seconds, artifact_dir=directory / "original" if directory else None)
    report = {"matroid_id": matroid.labelled_id(), "original": original.to_record(),
              "minors": [], "excluded": None, "proof_checked": False}
    if original.status == "SAT":
        report["excluded"] = False
    elif original.status == "UNSAT":
        unknown = False
        bad_minor = False
        for op in ("delete", "contract"):
            for e in range(matroid.n):
                minor = matroid.minor(e, op)
                result = represent(minor, seconds, artifact_dir=directory / f"{op}-{e}" if directory else None)
                report["minors"].append({"operation": op, "element": e,
                                         "groundset_in_parent_order": [x for x in range(matroid.n) if x != e],
                                         "result": result.to_record()})
                bad_minor |= result.status == "UNSAT"
                unknown |= result.status == "UNKNOWN"
        report["excluded"] = False if bad_minor else None if unknown else True
    if directory:
        (directory / "excluded.json").write_text(json.dumps(report, indent=2) + "\n")
    return report
