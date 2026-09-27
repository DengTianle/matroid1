"""Independent exact natural join of finite Boolean relations (no SAT)."""
from collections import defaultdict
from time import monotonic


def expand(coordinates, pattern):
    return sum((pattern >> j & 1) << (coordinate-1)
               for j, coordinate in enumerate(coordinates))


def solve_join(problem, seconds=60, max_intermediate=1000000):
    started = monotonic()
    tables = []
    for table in problem["tables"]:
        coordinates = table["coordinates"]
        mask = sum(1 << (coordinate-1) for coordinate in coordinates)
        patterns = {expand(coordinates, pattern) for pattern in table["patterns"]}
        tables.append((mask, patterns))
    mask, patterns = 0, {0}
    full_mask = (1 << problem["variables"])-1
    represented = set(problem["represented"])
    peak = 1
    while tables and patterns:
        if monotonic()-started >= seconds:
            return {"status":"UNKNOWN", "models":[], "seconds":monotonic()-started, "peak":peak}
        # Select the next relation by the exact cardinality of its join.
        choices = []
        for i, (other_mask, other_patterns) in enumerate(tables):
            overlap = mask & other_mask
            left_counts = defaultdict(int)
            right = defaultdict(list)
            for pattern in patterns:
                left_counts[pattern & overlap] += 1
            for pattern in other_patterns:
                right[pattern & overlap].append(pattern)
            size = sum(count*len(right[key]) for key, count in left_counts.items())
            choices.append((size, -(other_mask & ~mask).bit_count(), i, overlap, right))
        size, _, chosen, overlap, right = min(choices, key=lambda x:x[:3])
        if size > max_intermediate:
            return {"status":"UNKNOWN", "models":[], "seconds":monotonic()-started, "peak":peak,
                    "reason":"intermediate join bound"}
        other_mask, _ = tables.pop(chosen)
        patterns = {a | b for a in patterns for b in right[a & overlap]}
        mask |= other_mask
        peak = max(peak, len(patterns))
        if mask == full_mask:
            patterns.difference_update(represented)
    if patterns:
        assert mask == full_mask, "Relations do not cover every variable"
    patterns.difference_update(problem["represented"])
    clauses = problem.get("clauses", [])
    if clauses:
        patterns = {p for p in patterns if all(any(bool(p >> (abs(lit)-1) & 1) == (lit > 0)
                                                  for lit in clause) for clause in clauses)}
    return {"status":"EXHAUSTED", "models":sorted(patterns), "seconds":monotonic()-started,
            "peak":peak, "method":"exact natural join"}
