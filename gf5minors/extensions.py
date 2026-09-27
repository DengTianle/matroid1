"""All rank-preserving labelled extensions of one supplied deletion parent.

This is a completeness baseline, not a catalogue of all representable parents.
"""
from itertools import combinations
from time import monotonic

from .matroid import BasisMatroid
from .representation import solve_limited


def encode_extensions(parent, simple=False, cosimple=False):
    parent.validate()
    n, r = parent.n + 1, parent.r
    subsets = [frozenset(s) for s in combinations(range(n), r)]
    variables = {s: i + 1 for i, s in enumerate(subsets)}
    fixed = {variables[s]: s in parent.bases for s in subsets if parent.n not in s}
    clauses = [[v if value else -v] for v, value in fixed.items()]

    def add(literals):
        remaining = []
        for literal in literals:
            if abs(literal) in fixed:
                if fixed[abs(literal)] == (literal > 0):
                    return
            else:
                remaining.append(literal)
        if any(-literal in remaining for literal in remaining):
            return
        clauses.append(list(dict.fromkeys(remaining)))

    # A nonempty basis family is forced by the valid parent's fixed bases.
    for a in subsets:
        for b in subsets:
            difference = a - b
            if len(difference) < 2:  # These clauses are tautologies.
                continue
            for e in sorted(difference):
                add([-variables[a], -variables[b]] + [variables[(a - {e}) | {f}] for f in sorted(b - a)])
    for k in (1, 2):
        for subset in map(frozenset, combinations(range(n), k)):
            if simple:
                add([variables[b] for b in subsets if subset <= b])
            if cosimple:
                add([variables[b] for b in subsets if not subset & b])
    return subsets, clauses


def enumerate_extensions(parent, emit, *, simple=False, cosimple=False,
                         max_models=100, seconds=30, previous=()):
    """Call emit(M) for each NEW model. Resume by blocking validated previous ones.

    Exhaustion concerns only this labelled parent's constrained extensions.
    The time budget includes encoding; Slurm remains the hard outer limit.
    """
    from pysat.solvers import Solver
    if max_models < 1 or seconds <= 0:
        raise ValueError("positive limits required")
    started = monotonic()
    subsets, clauses = encode_extensions(parent, simple, cosimple)
    free = [(i + 1, b) for i, b in enumerate(subsets) if parent.n in b]

    def block(matroid):
        return [-v if b in matroid.bases else v for v, b in free]

    count = 0
    resumed = 0
    stop = "MODEL_LIMIT"
    with Solver(name="g4", bootstrap_with=clauses) as solver:
        for matroid in previous:
            matroid.validate()
            if matroid.n != parent.n + 1 or matroid.minor(parent.n, "delete") != parent:
                raise ValueError("resume record is not an extension of this parent")
            if simple and not matroid.is_simple() or cosimple and not matroid.dual().is_simple():
                raise ValueError("resume record violates filters")
            solver.add_clause(block(matroid))
            resumed += 1
        while count < max_models:
            answer = solve_limited(solver, seconds - (monotonic() - started))
            if answer is None:
                stop = "UNKNOWN"
                break
            if answer is False:
                stop = "EXHAUSTED"
                break
            model = set(solver.get_model())
            matroid = BasisMatroid(parent.n + 1, parent.r,
                                   frozenset(b for i, b in enumerate(subsets, 1) if i in model)).validate()
            if matroid.minor(parent.n, "delete") != parent:
                raise AssertionError("extension changed the deletion parent")
            emit(matroid)
            solver.add_clause(block(matroid))
            count += 1
    return {"status": stop, "new_models": count, "resumed_models": resumed,
            "seconds": monotonic() - started, "variables": len(subsets),
            "free_basis_variables": len(free), "clauses": len(clauses),
            "complete_for_fixed_labelled_parent": stop == "EXHAUSTED", "global_complete": False}

