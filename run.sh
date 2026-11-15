#!/bin/bash

source .venv/bin/activate
TTL_TOKEN=60

set -euo pipefail
LOG_DIR='./logs'
TIME_STAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/run_$TIME_STAMP.log"

mkdir -p "$LOG_DIR"

echo "Starting tests at $TIME_STAMP"
if pytest -v tests/ 2>&1 | tee "$LOG_FILE"; then
	echo "All tests passed"
else
	echo "Some cases error, see $LOG_FILE" >&2
        FAILED=$(grep -c "FAILED" "$LOG_FILE"||true)
	echo "Failed count: $FAILED"
	exit 1
fi
