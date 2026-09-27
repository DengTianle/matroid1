from itertools import combinations,product
import json
from pathlib import Path
import random
import unittest

from gf5minors.matroid import from_matrix,rank4_fixture,rank_mod
from gf5minors.projective import normalize,projective_points,extension_patterns
from gf5minors.table_sat import solve_problem
from gf5minors.table_join import solve_join


class RelationTests(unittest.TestCase):
    def test_random_relation_joins_against_exhaustive_assignments(self):
        rng = random.Random(51104)
        for _ in range(25):
            size = rng.randrange(1,7)
            tables = []
            for k in range(4):
                coordinates = sorted(rng.sample(range(1,size+1),rng.randrange(size+1)))
                patterns = [i for i in range(1 << len(coordinates)) if rng.randrange(2)]
                tables.append({"coordinates":coordinates,"patterns":patterns})
            forbidden = [i for i in range(1 << size) if rng.randrange(5)==0]
            expected = []
            for pattern in range(1 << size):
                if pattern in forbidden:
                    continue
                if all(sum((pattern >> (v-1) & 1) << j for j,v in enumerate(t["coordinates"])) in t["patterns"] for t in tables):
                    expected.append(pattern)
            result = solve_problem({"variables":size,"tables":tables,"represented":forbidden},seconds=10)
            self.assertEqual(result["status"],"EXHAUSTED")
            self.assertEqual(sorted(result["models"]),expected)
            tables.append({"coordinates":list(range(1,size+1)), "patterns":list(range(1 << size))})
            joined = solve_join({"variables":size,"tables":tables,"represented":forbidden},seconds=10)
            self.assertEqual(joined["status"],"EXHAUSTED")
            self.assertEqual(joined["models"],expected)

    def test_projective_point_count_and_normalization(self):
        self.assertEqual(len(projective_points(4)),156)
        a = [[1,0,0,0,1,1],[0,1,0,0,1,2],[0,0,1,0,2,3],[0,0,0,1,4,1]]
        scaled = [[x*(i+1)*((j+1)%4+1)%5 for j,x in enumerate(row)] for i,row in enumerate(a)]
        self.assertEqual(normalize(a,[0,1,2,3]),normalize(scaled,[0,1,2,3]))

    def test_vector_extension_patterns_with_independent_gaussian_oracle(self):
        a = [[1,0,0,0,1,1],[0,1,0,0,1,2],[0,0,1,0,2,3],[0,0,0,1,4,1]]
        expected = set()
        triples = list(combinations(range(6),3))
        existing = {tuple(row[j] for row in a) for j in range(6)}
        for vector in projective_points(4):
            if vector in existing:
                continue
            pattern = 0
            for i,triple in enumerate(triples):
                square = [[row[j] for j in triple]+[vector[k]] for k,row in enumerate(a)]
                if rank_mod(square)==4:
                    pattern |= 1 << i
            expected.add(pattern)
        self.assertEqual(set(extension_patterns([a])),expected)


if __name__ == "__main__":
    unittest.main()
