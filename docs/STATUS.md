Updated 27 September 2026 (Asia/Singapore).

**Classification completed: exactly 35 isomorphism classes.** The [complete catalogue](../results/r4-n11/CATALOGUE.md) gives exact hyperplane descriptions; [verification.json](../results/r4-n11/verification.json) records the finished checks. All 35 nonrepresentability proofs passed DRAT-trim, all 770 immediate-minor matrices passed independent Gaussian and Sage checks, and canonical incidence graphs confirmed pairwise nonisomorphism. None of the 35 matroids is paving; their triangle counts range from 4 to 13.

The complete ten-element parent catalogue contains 64,508 represented field-isomorphism classes, 58,756 abstract matroid classes, and 71,547 labelled projective representations. Every published rank-four excluded minor at sizes 7–10 has been reproduced and matched by exact isomorphism: 5, 92, 219, and 130 classes.

The SAT and independent finite-table methods agree on all nine-element parent problems and on the complete ten-element set of 5,991 labelled deletion-minimal candidates. The search method and its proof of coverage are documented in [DELETION_COMPATIBILITY.md](DELETION_COMPATIBILITY.md). The first eleven-element candidate has passed an independently checked DRAT nonrepresentability proof and explicit matrix checks for all 22 immediate minors.

Slurm array **884603** completed four disjoint ranges covering all 58,756 parent indices, each requesting one CPU, 4 GB RAM, and a one-hour limit in `normal`. The slowest range took 1,794.54 seconds, about 30 minutes. There were 84 disconnected parents excluded by the mathematical reduction, 58,672 exhausted connected-parent problems, 659 labelled deletion-minimal candidates, and zero UNKNOWN cases. Coverage audit/merge **884612**, nonrepresentation certification **884613**, minor certification **884614**, and final audit/report **884615** completed in dependency order. The certificates took about 17 and 37 seconds respectively. [Reproduction instructions](REPRODUCING.md) describe the workflow.

Catalogue SHA-256: `7940989ae051b32496dbfd7e4717d405431bcfd89da69d0dd522517552c76441`. The final result is a computational classification with a documented completeness proof and executable evidence; no claim of prior peer review or formally verified implementation is made.

The following paragraphs retain the historical initial-infrastructure validation, completed before the exhaustive research runs.

The existing `matroid1` environment supplies Python 3.11.16, python-sat 1.9.dev15 and NumPy 2.4.6. The separate `my-sage` environment supplies Sage 10.9. No packages were installed, no cluster configuration was changed, and no other users' jobs were accessed or modified.

Two small Slurm validation jobs, **883575** and **883585**, ran on `xcnc0`, each requesting one CPU, 2 GB RAM and a five-minute maximum in `normal`. The second includes the final command-line persistence checks and target-dimension encoding build. Those initial validation jobs finished; the user's interactive jobs were left untouched.

The final run produced the following evidence:

| Check | Result |
| --- | --- |
| Python test suite | 16 tests passed in 1.585 seconds |
| Known recognition cases | U(2,6) SAT; U(2,7), Fano, dual Fano and Vámos UNSAT |
| Excluded-minor regression | U(2,7), Fano and Vámos each passed all immediate-minor checks |
| Negative minimality check | U(2,8) correctly rejected as not minor-minimal |
| Small extension completeness | All five labelled extensions of U(2,3), matching both brute force and Sage |
| Simple line extension | Only U(2,7) from U(2,6), then solver exhaustion |
| Interrupted/resumed enumeration | Same coverage, no repeated models; changed filters refused |
| Sage rank/minor comparison | 2,472 subset ranks checked, plus all immediate minors of six fixtures |
| Witness comparison using Sage | 14 saved GF(5) matrices checked |
| Canonical-label comparison | Relabeling invariance checked on six fixtures |
| Rank-4, 11-element represented fixture | SAT witness verified; 1,379 variables, 9,079 clauses, approximately 0.263 seconds |
| Target-dimension extension CNF | 330 basis variables, 120 free, 69,423 clauses for one fixture parent; approximately 0.928 seconds to build |
| Author reference snapshots | Four files, 170,299 bytes total, SHA-256 checked; not executed or unpickled |

The last two timing measurements concern one constructed represented fixture and one encoding build, respectively. They are not estimates of the cost of enumerating all parents or candidates. No target-size extension models were requested.

Run records:

- [Final test log](../runs/slurm-gf5-smoke-883585.err) and [output log](../runs/slurm-gf5-smoke-883585.out).
- [Sage validation](../runs/smoke-883585/sage-validation.json), [environment](../runs/smoke-883585/doctor.json), and [provenance](../runs/smoke-883585/environment.json).
- [Target-dimension encoding statistics](../runs/smoke-883585/target-encoding.json).
- [Fano excluded-minor report](../runs/smoke-883585/excluded-F7/excluded.json), with representations of all 14 immediate minors and the original UNSAT instance/proof in adjacent directories.
- [Reference-file manifest](../data/reference_manifest.json) and [published calibration counts](../data/known_counts.json).

The mathematical package source digest for this run is `b531249f1a4b28a8a7083af2a7158dcde915dec0e495b8edf24508c819f5fd54`. Run artifacts and raw external files are ignored by Git; the small portable fixtures and reference manifest are project files.

The initial-run artifacts above retain their original flags. Subsequent work imported all 2,692 published records using a pinned hash and constructor allowlist, generated the complete represented parent catalogues, reproduced all rank-four calibration slices, and added the pinned local DRAT-trim checker. The eleven-element enumeration and final certification are complete.
