#!/bin/sh
set -eu
cd /app
results_dir=${ASTROMATCH_RESULTS_DIR:-/app/engine/out}
mkdir -p "$results_dir"
mode=$(python -c 'from backend.app.services.data import initialize_dataset; print(initialize_dataset().mode)')
run_engine() {
    if [ "$mode" = mock ]; then
        python -m engine.cli "$1" --mock --preset all --out "$results_dir"
    else
        python -m engine.cli "$1" --preset all --out "$results_dir"
    fi
}
if [ "${1:-}" = precompute ]; then
    run_engine run
    if [ "$mode" = mock ]; then
        python -m engine.cli validate --mock --out "$results_dir"
    else
        python -m engine.cli validate --out "$results_dir"
    fi
    exit 0
fi
if [ "${ASTROMATCH_PRECOMPUTE:-0}" = 1 ] && [ -z "$(find "$results_dir" -maxdepth 1 -type f -print -quit)" ]; then
    run_engine run
fi
exec uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --workers "${ASTROMATCH_WORKERS:-1}"
