The exhaustive computation finds **exactly 35 isomorphism classes of rank-4, 11-element excluded minors for GF(5)-representability**. The [complete catalogue](results/r4-n11/CATALOGUE.md) specifies each matroid exactly by its hyperplanes; [basis-bit records](results/r4-n11/excluded.jsonl) and [verification results](results/r4-n11/verification.json) are also provided.

All 58,756 simple represented ten-element parent classes were covered: 84 disconnected parents were excluded by the 3-connectivity reduction, and all 58,672 connected-parent searches were exhausted without UNKNOWN results. After contraction checks and isomorphism deduplication, all 35 retained matroids passed separate determinant-CNF/DRAT nonrepresentability checks, and all 770 immediate-minor matrices passed modular Gaussian and Sage verification. Canonical incidence graphs independently confirmed distinctness. This is a computational classification; its mathematical completeness argument and executable evidence are supplied for review.

The package provides labelled basis records, deletion/contraction, exact GF(5) recognition using PySAT, independent matrix-witness checking, immediate-minor verification, resumable SAT generation of a supplied parent's extensions, and optional Sage isomorphism keys. The [design note](docs/DESIGN.md) explains the encodings and the remaining completeness obligations. See [validation status](docs/STATUS.md) for actual runs.

Use the existing environments; no installation is needed from the repository root:

```bash
# Run small checks through Slurm. The tracked runs/ directory holds the logs.
sbatch slurm/smoke.slurm
```

For commands in an **existing Slurm allocation**, the following creates fixtures and a bounded extension run:

```bash
/home/t/tianle51/miniconda3/envs/matroid1/bin/python -m gf5minors fixtures --output data/fixtures
/home/t/tianle51/miniconda3/envs/matroid1/bin/python -m gf5minors extend data/fixtures/U2_6.json --simple --max-models 2 --seconds 30 --output runs/line-example
```

`fixtures` expects a new directory. If the supplied `data/fixtures` already exists, use it directly or choose another output path. Likewise, recognition and new extension runs require new output directories so existing artifacts are not overwritten.

```bash
# A bounded excluded-minor check: one CPU, 2 GB, five-minute outer limit.
sbatch slurm/recognize.slurm data/fixtures/F7.json

# Inside an allocation, test a single supplied matroid and save a CNF/witness/proof.
/home/t/tianle51/miniconda3/envs/matroid1/bin/python -m gf5minors represent data/fixtures/rank4_11_representable.json --seconds 30 --output runs/represented-example

# Resume an extension journal with the same input and filters.
/home/t/tianle51/miniconda3/envs/matroid1/bin/python -m gf5minors extend data/fixtures/U2_6.json --simple --max-models 2 --seconds 30 --output runs/line-example --resume
```

`--seconds` is a per-recognition-call budget: checking an 11-element excluded minor can invoke recognition 23 times. Slurm supplies the hard outer limit. Solver expiration produces `UNKNOWN`; it is never interpreted as UNSAT. A killed job or a journal without a completed summary is incomplete. Extension exhaustion covers one supplied labelled parent only. Use one process per requested CPU; the Slurm templates cap numerical-library thread counts and request no GPUs or special nodes.

The environments are separate: `matroid1` supplies Python/PySAT, and `my-sage` supplies Sage. The pure basis-record format allows exchange without installing PySAT into Sage. For example, inside an allocation:

```python
# Run this with /home/t/tianle51/miniconda3/envs/my-sage/bin/python
from gf5minors.matroid import fano
from gf5minors.sage_bridge import canonical_key
print(canonical_key(fano()))
```

Reference metadata and published calibration counts are in `data/`. `scripts/fetch_references.py` caches the author's linked Sage source/catalogue as inert files under `data/raw/` and records checksums. Downloaded scripts and Sage pickles are not automatically loaded. The initial framework does not depend on executing them.

The [deletion-compatibility reduction](docs/DELETION_COMPATIBILITY.md) supplies the search method. It reproduced every published rank-four excluded minor at sizes seven through ten (5, 92, 219, and 130 classes), with exact isomorphism comparison. SAT and independent finite-table joins agree on every nine-element parent and on all 5,991 labelled ten-element candidates. The ten-element parent catalogue retains 64,508 field-isomorphism classes and 71,547 labelled representations. The target search produced 659 labelled deletion-minimal candidates and the final 35 classes. See [reproduction instructions](docs/REPRODUCING.md) and the [literature review](docs/LITERATURE.md). Historical initial-run records retain their original `proof_checked: false` values.
