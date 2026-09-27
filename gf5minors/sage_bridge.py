"""Optional exact isomorphism keys; run with the existing my-sage Python."""
from itertools import combinations

from .matroid import BasisMatroid


def to_sage(matroid):
    from sage.all import Matroid
    return Matroid(groundset=list(range(matroid.n)), bases=[list(b) for b in matroid.bases])


def from_sage(matroid):
    # A specified order is preserved when labels already are 0,...,n-1.
    ground = sorted(matroid.groundset())
    labels = {e: i for i, e in enumerate(ground)}
    return BasisMatroid(len(ground), int(matroid.rank()), frozenset(
        frozenset(labels[e] for e in b) for b in matroid.bases()))


def canonical_key(matroid):
    """Full exact key of a colored incidence graph, not just a hash.

    The ground-set vertices and subset vertices have distinct colors.
    This canonical format is tied to Sage's 'sage' graph-labeling backend.
    """
    from sage.all import Graph
    all_subsets = frozenset(map(frozenset, combinations(range(matroid.n), matroid.r)))
    nonbases = all_subsets - matroid.bases
    use_bases = len(matroid.bases) <= len(nonbases)
    family = matroid.bases if use_bases else nonbases
    family = sorted(family, key=lambda b: tuple(sorted(b)))
    graph = Graph()
    graph.add_vertices(range(matroid.n + len(family)))
    for index, subset in enumerate(family, matroid.n):
        graph.add_edges((index, e) for e in sorted(subset))
    partition = [list(range(matroid.n)), list(range(matroid.n, matroid.n + len(family)))]
    canonical = graph.canonical_label(partition=[part for part in partition if part], algorithm="sage")
    return f"gf5-incidence-v1:{matroid.n}:{matroid.r}:{int(use_bases)}:{canonical.graph6_string()}"

