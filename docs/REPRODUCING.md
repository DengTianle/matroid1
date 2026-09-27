The search is an exhaustive computation over finite sets. Its mathematical coverage argument is in [DELETION_COMPATIBILITY.md](DELETION_COMPATIBILITY.md). Run computation through Slurm, using one CPU per process and the existing `my-sage` and `matroid1` environments.

The main stages, in dependency order, are:

1. Generate every simple rank-four represented field-isomorphism class through ten elements with `scripts/generate_parents.py --rank 4 --max-size 10 --output data/parents`. Generate simple rank-three classes through ten with the same script and `--rank 3 --output data/parents-r3`. The generation starts with an identity matrix. Completed levels are reused; an unfinished level is not a completed catalogue.
2. For ranks four and sizes 5–10, run `scripts/prepare_representations.py --size N`. This aligns all field classes with their abstract parent and closes them under its full automorphism group, retaining all labelled projective representations.
3. Run `scripts/search_compatible_deletions.py --size 11 --method join --start A --stop B --seconds 3300 --output NEW_DIRECTORY`. The half-open parent-index ranges must partition `[0,58756)`. The four-task wrapper `scripts/search_array.py --shards 4 --size 11 --output runs/NEW_RUN` chooses disjoint ranges from `SLURM_ARRAY_TASK_ID`. `--method sat` is the alternative solver; `--method both` compares both methods on each problem.
4. Run `scripts/merge_search.py SHARD_DIRECTORIES... --output NEW_RESULT_DIRECTORY`. This rejects incomplete ranges, overlaps, missing parents, UNKNOWN cases, and inconsistent input/code fingerprints. It deduplicates by exact matroid isomorphism and exports the full basis-bit and hyperplane descriptions.
5. Run `scripts/certify_nonrepresentation.py NEW_RESULT_DIRECTORY/excluded.jsonl --output NEW_RESULT_DIRECTORY/nonrepresentation` with the PySAT environment. Run `scripts/certify_minors.py` on the same input with the Sage environment and `--output NEW_RESULT_DIRECTORY/minors`. The former emits a separate determinant CNF and DRAT proof for each matroid and checks it with the pinned local DRAT-trim binary. The latter constructs and checks matrices for every deletion and contraction.
6. Run `scripts/final_audit.py NEW_RESULT_DIRECTORY` with Sage. This checks certificate coverage and input fingerprints, independently tests distinctness using canonical colored incidence graphs, and creates the human-readable catalogue.

Use `sbatch slurm/research.slurm sage SCRIPT ARGUMENTS...` or `sbatch slurm/research.slurm sat SCRIPT ARGUMENTS...` to select an environment. Override the default twenty-minute limit only when a longer allocation is needed. The main search uses four one-CPU tasks, 4 GB each, in the ordinary `normal` partition; no other users' jobs or system configuration are modified.

For a clean reproduction, use a separate copy of the repository and new output directories. Existing completed parent levels are intentionally reused by the generation script. Every search run snapshots its source files and hashes its parent/minor catalogues in `manifest.json`. Parent logs contain the input-table hash, solution-set hash, and exhaustion status. Final catalogues store one basis bit per lexicographically ordered four-subset: bit zero refers to `(0,1,2,3)`, and a set is a basis exactly when its bit is one.

The calibration commands are identical with target sizes 7, 8, 9, and 10. Their exact isomorphism-class counts are 5, 92, 219, and 130. `scripts/compare_catalogue.py` compares the outputs with Brettell's imported published catalogue, and `scripts/compare_searches.py` compares the complete labelled candidate sets of two independent runs. The import is pinned to the original archive's SHA-256 and uses an explicit pickle-constructor allowlist.

The DRAT checker source is pinned in `vendor/drat-trim/manifest.json` and includes its upstream license. Build it locally through `sbatch slurm/research.slurm sat scripts/build_drat.py`. No package installation or administrative privileges are required. The proof checker establishes unsatisfiability of each supplied determinant CNF; the mathematical encoding and exhaustive-search coverage remain part of the computational proof and are documented separately.

The saved minor matrices can be checked without Sage, using the pure Python basis and modular linear-algebra code:

```python
import json
from pathlib import Path
from gf5minors.compact import unpack
from gf5minors.matroid import verify_representation

for line in Path("results/r4-n11/minors/minor-witnesses.jsonl").read_text().splitlines():
    case = json.loads(line)
    matroid = unpack(case["matroid"])
    for witness in case["witnesses"]:
        minor = matroid.minor(witness["element"], witness["operation"])
        assert verify_representation(minor, witness["matrix"])
```

For any class index `NNNN`, independently replay its nonrepresentability proof with `vendor/drat-trim/drat-trim results/r4-n11/nonrepresentation/matroid-NNNN/representation.cnf results/r4-n11/nonrepresentation/matroid-NNNN/proof.drat`. Proof directories use zero-based indices; human class IDs use one-based numbering. A successful replay prints `s VERIFIED`.

The Slurm wrapper and the worker launcher contain interpreter paths for this cluster's existing environments. On another machine, these paths must be adjusted to the local Sage and PySAT interpreters; the catalogue and certificate formats themselves are independent of those paths.
