"""Exact normalized representations and vector-extension truth tables over GF(5)."""
from collections import deque
from itertools import combinations, product
import numpy as np


def normalize(matrix, basis):
    """Fix basis coordinates and a deterministic support-graph forest gauge."""
    a = [[int(x) % 5 for x in row] for row in matrix]
    r, n = len(a), len(a[0])
    for i, column in enumerate(basis):
        pivot = next(k for k in range(i, r) if a[k][column])
        a[i], a[pivot] = a[pivot], a[i]
        scale = pow(a[i][column], -1, 5)
        a[i] = [scale*x % 5 for x in a[i]]
        for k in range(r):
            if k != i:
                scale = a[k][column]
                a[k] = [(x-scale*y) % 5 for x, y in zip(a[k], a[i])]
    outside = [j for j in range(n) if j not in basis]
    row_scales = [None]*r
    column_scales = [None]*n
    for root in range(r):
        if row_scales[root] is not None:
            continue
        row_scales[root] = 1
        queue = deque([(True, root)])
        while queue:
            is_row, index = queue.popleft()
            if is_row:
                for j in outside:
                    if a[index][j] and column_scales[j] is None:
                        column_scales[j] = pow(row_scales[index]*a[index][j] % 5, -1, 5)
                        queue.append((False, j))
            else:
                for i in range(r):
                    if a[i][index] and row_scales[i] is None:
                        row_scales[i] = pow(column_scales[index]*a[i][index] % 5, -1, 5)
                        queue.append((True, i))
    for i, j in enumerate(basis):
        column_scales[j] = pow(row_scales[i], -1, 5)
    return tuple(tuple(a[i][j]*row_scales[i]*(column_scales[j] or 1) % 5 for j in range(n)) for i in range(r))


def permute(matrix, permutation):
    a = [[0]*len(permutation) for _ in matrix]
    for i, row in enumerate(matrix):
        for j, image in enumerate(permutation):
            a[i][image] = int(row[j])
    return a


def representation_orbit(matrices, basis, generators):
    seen = {normalize(matrix, basis) for matrix in matrices}
    queue = deque(sorted(seen))
    while queue:
        matrix = queue.popleft()
        for permutation in generators:
            candidate = normalize(permute(matrix, permutation), basis)
            if candidate not in seen:
                seen.add(candidate)
                queue.append(candidate)
    return sorted(seen)


def projective_points(r):
    return [tuple([0]*i+[1]+list(tail)) for i in range(r) for tail in product(range(5), repeat=r-i-1)]


def extension_patterns(matrices, simple=True):
    """Basis bits for triples + the new element, in lexicographic triple order.

    Matrices must have rank four, the same labelled matroid, and cover every
    labelled projective representation class. Patterns include all vectors of
    PG(3,5), with existing point directions removed for simple extensions.
    """
    points = np.array(projective_points(4), dtype=np.int64).T
    patterns = set()
    for matrix in matrices:
        a = np.array(matrix, dtype=np.int64)
        if a.shape[0] != 4:
            raise ValueError("rank-four matrices required")
        triples = np.array(list(combinations(range(a.shape[1]), 3)))
        # v is (#triples, 4, 3); cofactors are perpendicular to each triple.
        v = a[:, triples].transpose(1, 0, 2)
        normals = np.zeros((len(triples), 4), dtype=np.int64)
        for row in range(4):
            w = v[:, [i for i in range(4) if i != row], :]
            det = (w[:,0,0]*(w[:,1,1]*w[:,2,2]-w[:,1,2]*w[:,2,1])
                   - w[:,0,1]*(w[:,1,0]*w[:,2,2]-w[:,1,2]*w[:,2,0])
                   + w[:,0,2]*(w[:,1,0]*w[:,2,1]-w[:,1,1]*w[:,2,0]))
            normals[:, row] = ((-1)**row*det) % 5
        nonzero = (normals @ points) % 5 != 0
        packed = np.packbits(nonzero.T, axis=1, bitorder="little")
        used = set()
        if simple:
            for j in range(a.shape[1]):
                column = [int(x) for x in a[:,j]]
                first = next((x for x in column if x), None)
                if first is not None:
                    inverse = pow(first, -1, 5)
                    used.add(tuple(x*inverse % 5 for x in column))
        for point, packed_row in zip(points.T, packed):
            if tuple(map(int, point)) not in used:
                patterns.add(int.from_bytes(packed_row.tobytes(), "little"))
    return sorted(patterns)
