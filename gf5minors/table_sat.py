"""Exact finite-relation joins, encoded as shared reduced decision diagrams."""
from time import monotonic
from .representation import solve_limited


class TablesCNF:
    def __init__(self, variables):
        self.variables = variables
        self.nv = variables + 1
        self.true = self.nv
        self.clauses = [[self.true]]
        self.nodes = {}

    def clause(self, literals):
        literals = set(literals)
        if self.true in literals or any(-literal in literals for literal in literals):
            return
        literals.discard(-self.true)
        self.clauses.append(sorted(literals))

    def node(self, variable, low, high):
        if low == high:
            return low
        if (low, high) == (-self.true, self.true):
            return variable
        if (low, high) == (self.true, -self.true):
            return -variable
        key = (variable, low, high)
        if key not in self.nodes:
            self.nv += 1
            node = self.nv
            # node <=> (variable ? high : low)
            self.clause([-node, variable, low])
            self.clause([-node, -variable, high])
            self.clause([node, variable, -low])
            self.clause([node, -variable, -high])
            self.nodes[key] = node
        return self.nodes[key]

    def allow(self, coordinates, patterns):
        coordinates = list(coordinates)
        patterns = sorted(set(patterns))
        # Retain a consistent global order, enabling sharing across tables.
        if coordinates != sorted(coordinates) or len(set(coordinates)) != len(coordinates):
            raise ValueError("table coordinates must be distinct and increasing")
        if any(p < 0 or p >> len(coordinates) for p in patterns):
            raise ValueError("invalid table pattern")
        def recurse(position, rows):
            if not rows:
                return -self.true
            if position == len(coordinates):
                return self.true
            low = [row for row in rows if not (row >> position & 1)]
            high = [row for row in rows if row >> position & 1]
            return self.node(coordinates[position], recurse(position+1, low), recurse(position+1, high))
        self.clause([recurse(0, patterns)])

    def forbid(self, pattern):
        self.clause([-i if pattern >> (i-1) & 1 else i for i in range(1, self.variables+1)])


def solve_problem(problem, seconds=60):
    from pysat.solvers import Solver
    started = monotonic()
    cnf = TablesCNF(problem["variables"])
    for table in problem["tables"]:
        cnf.allow(table["coordinates"], table["patterns"])
    for pattern in problem["represented"]:
        cnf.forbid(pattern)
    for clause in problem.get("clauses", []):
        cnf.clause(clause)
    models = []
    with Solver(name="g4", bootstrap_with=cnf.clauses) as solver:
        while True:
            answer = solve_limited(solver, seconds-(monotonic()-started))
            if answer is None:
                status = "UNKNOWN"
                break
            if answer is False:
                status = "EXHAUSTED"
                break
            assignment = set(solver.get_model())
            pattern = sum(1 << (i-1) for i in range(1,cnf.variables+1) if i in assignment)
            models.append(pattern)
            solver.add_clause([-i if i in assignment else i for i in range(1,cnf.variables+1)])
    return {"status":status,"models":models,"variables":cnf.nv,"clauses":len(cnf.clauses),
            "seconds":monotonic()-started}
