#!/usr/bin/env bash
# Reproduces every relay study result in results/. Every model call is replayed from results/cache,
# so rerunning makes no new calls and gives byte identical outputs.
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONIOENCODING=utf-8
COMMON="--tasks 8 --samples 2 --depths 4 --budget 150 --rounds 2 --loop-depths 0,1,4 --workers ${WORKERS:-10}"
for scale in 1 4; do
  for mode in brief summary; do
    echo "=== compress=$mode scale=$scale"
    python run.py --compress $mode --scale $scale $COMMON --out results/${mode}_s${scale}
    python analyze.py results/${mode}_s${scale} > /dev/null
  done
done
echo "=== control: Root reviews from its own compacted notes"
python run.py --compress summary --scale 4 $COMMON --loop-depths 1,4 --conds B,Bc --out results/summary_s4_compacted_root
python analyze.py results/summary_s4_compacted_root > /dev/null
python figures.py results
echo "all runs complete"
