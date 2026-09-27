import itertools
import json
import random
from tempfile import TemporaryDirectory
from pathlib import Path
import unittest
from unittest.mock import patch

from gf5minors.matroid import (BasisMatroid, fano, from_matrix, rank4_fixture,
                               rank_mod, uniform, vamos, verify_representation)
from gf5minors.extensions import enumerate_extensions
from gf5minors.representation import (check_excluded, encode_representation,
                                      represent, RepresentationResult, solve_limited)


class MatroidTests(unittest.TestCase):
    def test_known_basis_counts_and_exchange(self):
        self.assertEqual(len(fano().validate().bases), 28)
        self.assertEqual(len(vamos().validate().bases), 65)
        self.assertEqual(rank_mod([[1, 2], [2, 4]]), 1)
        with self.assertRaises(ValueError):
            BasisMatroid(4, 2, frozenset((frozenset((0, 1)), frozenset((2, 3))))).validate()

    def test_minor_duality_including_loops_and_coloops(self):
        fixtures = [fano(), vamos(), from_matrix([[1, 0, 1, 0], [0, 1, 0, 0]]), uniform(0, 2), uniform(2, 2)]
        for matroid in fixtures:
            self.assertEqual(matroid.dual().dual(), matroid)
            for e in range(matroid.n):
                self.assertEqual(matroid.minor(e, "delete").dual(), matroid.dual().minor(e, "contract"))
                matroid.minor(e, "delete").validate()
                matroid.minor(e, "contract").validate()

    def test_record_roundtrip_and_invalid_input(self):
        for matroid in [fano(), vamos(), uniform(0, 0)]:
            self.assertEqual(BasisMatroid.from_record(json.loads(json.dumps(matroid.to_record()))), matroid)
        record = uniform(1, 2).to_record()
        record["bases"].append([0])
        with self.assertRaises(ValueError):
            BasisMatroid.from_record(record)


class RepresentationTests(unittest.TestCase):
    def test_known_positive_and_negative_instances(self):
        for matroid, status in [(uniform(2, 6), "SAT"), (uniform(2, 7), "UNSAT"),
                                (fano(), "UNSAT"), (fano().dual(), "UNSAT"), (vamos(), "UNSAT")]:
            with self.subTest(n=matroid.n, r=matroid.r, bases=len(matroid.bases)):
                result = represent(matroid, seconds=20)
                self.assertEqual(result.status, status)
                if status == "SAT":
                    self.assertTrue(verify_representation(matroid, result.matrix))

    def test_all_single_element_minors(self):
        for matroid in [uniform(2, 7), fano(), vamos()]:
            report = check_excluded(matroid, seconds=10)
            self.assertIs(report["excluded"], True)
            self.assertEqual(len(report["minors"]), 2 * matroid.n)
            self.assertTrue(all(m["result"]["witness_checked"] for m in report["minors"]))
            self.assertFalse(report["proof_checked"])

    def test_representation_and_nonminimal_obstruction_are_rejected(self):
        self.assertFalse(check_excluded(uniform(2, 6))["excluded"])
        self.assertFalse(check_excluded(uniform(2, 8))["excluded"])

    def test_random_represented_matrices_and_target_size(self):
        rng = random.Random(511)
        fixtures = [rank4_fixture()]
        for r in range(1, 5):
            for _ in range(3):
                fixtures.append(from_matrix([[rng.randrange(5) for _ in range(r + 3)] for _ in range(r)]))
        for matroid in fixtures:
            result = represent(matroid, seconds=20)
            self.assertEqual(result.status, "SAT")
            self.assertTrue(verify_representation(matroid, result.matrix))

    def test_loops_coloops_zero_rank_and_disconnected_support(self):
        for matroid in [uniform(0, 3), uniform(0, 0), uniform(3, 3),
                        from_matrix([[1, 1, 0, 0, 0], [0, 0, 1, 1, 0]])]:
            result = represent(matroid)
            self.assertEqual(result.status, "SAT")
            self.assertTrue(verify_representation(matroid, result.matrix))

    def test_forest_normalization_preserves_answer(self):
        for matroid in [fano(), uniform(2, 6), from_matrix([[1, 1, 0, 0], [0, 0, 1, 1]])]:
            self.assertEqual(represent(matroid).status, represent(matroid, normalize=False).status)

    def test_unknown_never_means_unsat(self):
        self.assertEqual(represent(fano(), seconds=0).status, "UNKNOWN")
        unknown = RepresentationResult("UNKNOWN", 0, 0, 0)
        unsat = RepresentationResult("UNSAT", 0, 0, 0)
        with patch("gf5minors.representation.represent", return_value=unknown):
            self.assertIsNone(check_excluded(fano())["excluded"])
        with patch("gf5minors.representation.represent", side_effect=[unsat] + [unknown] * 14):
            self.assertIsNone(check_excluded(fano())["excluded"])

    def test_saved_cnf_and_proof_are_replayable(self):
        from pysat.formula import CNF
        from pysat.solvers import Solver
        with TemporaryDirectory() as tmp:
            for name, matroid, expected in [("fano", fano(), False), ("line", uniform(2, 6), True)]:
                directory = Path(tmp) / name
                result = represent(matroid, artifact_dir=directory)
                cnf = CNF(from_file=str(directory / "representation.cnf"))
                # Different SAT engine; this checks a saved instance, not a DRAT proof.
                with Solver(name="m22", bootstrap_with=cnf.clauses) as solver:
                    self.assertEqual(solver.solve(), expected)
                if not expected:
                    self.assertTrue(result.proof_written)
                    self.assertTrue((directory / "proof.drat").exists())
                    self.assertFalse(result.proof_checked)


class ExtensionTests(unittest.TestCase):
    def test_complete_small_family_against_independent_bruteforce(self):
        # All subsets of the three possible new bases; no SAT in the oracle.
        parent = uniform(2, 3)
        expected = set()
        new_bases = [frozenset((i, 3)) for i in range(3)]
        for bits in itertools.product([False, True], repeat=3):
            candidate = BasisMatroid(4, 2, parent.bases | frozenset(b for b, bit in zip(new_bases, bits) if bit))
            try:
                candidate.validate()
            except ValueError:
                continue
            expected.add(candidate)
        actual = []
        report = enumerate_extensions(parent, actual.append, max_models=20)
        self.assertEqual(len(expected), 5)  # loop, 3 parallel placements, generic
        self.assertEqual(set(actual), expected)
        self.assertTrue(report["complete_for_fixed_labelled_parent"])
        self.assertFalse(report["global_complete"])

    def test_known_excluded_extension_and_resume(self):
        actual = []
        report = enumerate_extensions(uniform(2, 6), actual.append, simple=True, max_models=2)
        self.assertEqual(actual, [uniform(2, 7)])
        self.assertEqual(report["status"], "EXHAUSTED")
        parent = uniform(2, 3)
        first = []
        partial = enumerate_extensions(parent, first.append, max_models=2)
        self.assertFalse(partial["complete_for_fixed_labelled_parent"])
        rest = []
        final = enumerate_extensions(parent, rest.append, previous=first, max_models=10)
        self.assertEqual(len(set(first + rest)), 5)
        self.assertEqual(final["status"], "EXHAUSTED")

    def test_cosimple_filter_and_zero_rank(self):
        actual = []
        enumerate_extensions(uniform(2, 3), actual.append, cosimple=True, max_models=20)
        self.assertTrue(actual)
        self.assertTrue(all(m.dual().is_simple() for m in actual))
        actual = []
        report = enumerate_extensions(uniform(0, 2), actual.append, max_models=2)
        self.assertEqual(actual, [uniform(0, 3)])
        self.assertEqual(report["status"], "EXHAUSTED")


if __name__ == "__main__":
    unittest.main()
