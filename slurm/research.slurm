#!/bin/bash
#SBATCH --job-name=gf5-research
#SBATCH --partition=normal
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:20:00
#SBATCH --output=runs/research-%j.out
#SBATCH --error=runs/research-%j.err
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?Submit from repository root}"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
export DOT_SAGE="$PWD/runs/sage-state-${SLURM_JOB_ID}"
case "${1:?Specify sage or sat}" in
  sage) GF5_RESEARCH_PYTHON=/home/t/tianle51/miniconda3/envs/my-sage/bin/python ;;
  sat) GF5_RESEARCH_PYTHON=/home/t/tianle51/miniconda3/envs/matroid1/bin/python ;;
  *) exit 2 ;;
esac
shift
"$GF5_RESEARCH_PYTHON" "$@"
