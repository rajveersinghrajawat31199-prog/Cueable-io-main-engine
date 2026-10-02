#!/usr/bin/env bash
# One command for the deterministic half of the gate: machine axes + review sheets, both timed. Then LOOK at the sheets and log a review round.
# usage: run_gate.sh <project-dir> <video> --profile ui-morph-loop [--tier standard] [--run-check]
set -euo pipefail
PROJ="${1:?project dir}"; VID="${2:?video}"; shift 2
PROFILE=default; TIER=standard; EXTRA=()
while [ $# -gt 0 ]; do case "$1" in --profile) PROFILE="$2"; shift 2;; --tier) TIER="$2"; shift 2;; --run-check) EXTRA+=(--run-check); shift;; *) echo "unknown $1"; exit 1;; esac; done
QG="$(cd "$(dirname "$0")" && pwd)"; cd "$PROJ"
python3 "$QG/stage_timer.py" run --stage machine-scores --tag gate -- python3 "$QG/machine_scores.py" "$VID" --profile "$PROFILE" --project . ${EXTRA[@]+"${EXTRA[@]}"}
python3 "$QG/stage_timer.py" run --stage make-sheets --tag gate -- python3 "$QG/make_sheets.py" "$VID" --project .
echo; echo "NEXT: open quality/sheets/*.png, score the vision axes (references/review-protocol.md), write quality/review/round-N.json"
echo "      then: python3 $QG/gate.py evaluate --tier $TIER --profile $PROFILE --project ."
