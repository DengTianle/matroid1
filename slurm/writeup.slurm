#!/bin/bash
#SBATCH --job-name=gf5-writeup-pdf
#SBATCH --partition=normal
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:05:00
#SBATCH --output=runs/writeup-pdf-%j.out
#SBATCH --error=runs/writeup-pdf-%j.err
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?Submit from repository root}"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export XDG_CACHE_HOME="$PWD/runs/writeup-tex-cache"
GF5_WRITEUP_TEX="${GF5_WRITEUP_TEX:-$PWD/runs/writeup-tools/tectonic}"
if [[ ! -x "$GF5_WRITEUP_TEX" ]]; then
    echo 'Set GF5_WRITEUP_TEX to an installed Tectonic compiler.' >&2
    exit 2
fi
mkdir -p "$XDG_CACHE_HOME"
cd paper
"$GF5_WRITEUP_TEX" --untrusted --keep-logs main.tex
