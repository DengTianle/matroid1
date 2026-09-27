#!/bin/bash
#SBATCH --job-name=gf5-recognize
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
# Usage: sbatch slurm/recognize.slurm data/fixtures/F7.json
# 10 seconds per call; for n=11, at most 23 recognition calls.
"$GF5_PYTHON" -m gf5minors excluded "${1:?Pass a matroid JSON path}" \
    --seconds 10 --output "runs/recognize-${SLURM_JOB_ID}"
