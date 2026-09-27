#!/bin/bash
#SBATCH --job-name=gf5-smoke
#SBATCH --partition=normal
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:05:00
#SBATCH --output=runs/slurm-%x-%j.out
#SBATCH --error=runs/slurm-%x-%j.err

set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?Submit from the project root}"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
GF5_PYTHON="${GF5_PYTHON:-/home/t/tianle51/miniconda3/envs/matroid1/bin/python}"
GF5_SAGE_PYTHON="${GF5_SAGE_PYTHON:-/home/t/tianle51/miniconda3/envs/my-sage/bin/python}"
GF5_RUN_DIR="$PWD/runs/smoke-${SLURM_JOB_ID}"
mkdir -p "$GF5_RUN_DIR"
export DOT_SAGE="$GF5_RUN_DIR/sage-state"
"$GF5_PYTHON" scripts/doctor.py > "$GF5_RUN_DIR/doctor.json"
"$GF5_PYTHON" -m unittest discover -s tests -p 'test_*.py' -v
"$GF5_PYTHON" scripts/smoke.py "$GF5_RUN_DIR"
"$GF5_SAGE_PYTHON" tests/sage_check.py "$GF5_RUN_DIR"
"$GF5_PYTHON" scripts/prepare_data.py "$GF5_RUN_DIR"
