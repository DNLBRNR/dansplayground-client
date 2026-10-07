#!/bin/bash
set -euo pipefail
BASE="$(cd "$(dirname "$0")" && pwd)"
export XDG_CONFIG_HOME="$BASE/config"
export HOME="$BASE/home"
export CALIBRATION_STORE="$BASE/cache"
export AUTODARTS_CONFIG="$XDG_CONFIG_HOME/autodarts/config.toml"
export AUTODARTS_API="${AUTODARTS_API:-http://127.0.0.1:3180}"
export GOOD_CALIBRATION_API="$BASE/captured-calibration-api.json"

if [ ! -f "$BASE/good-calibration.toml" ]; then
    echo "[Dan's Playground V13] Bitte zuerst ./setup-test.sh ausführen."
    exit 1
fi

cp -f "$BASE/good-calibration.toml" "$AUTODARTS_CONFIG"

# Local offline calibration endpoint stays in place. No cloud calibration is used.
python3 "$BASE/calibration_server_offline.py" &
CALIBRATION_PID=$!

# Start Autodarts first. The V13 watcher must capture the real GET response from
# the running process, not synthesize an API object from TOML.
"$BASE/autodarts" &
AUTODARTS_PID=$!

cleanup() {
    kill "$RESTORE_PID" 2>/dev/null || true
    kill "$CALIBRATION_PID" 2>/dev/null || true
    kill "$AUTODARTS_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

python3 "$BASE/restore_calibration.py" &
RESTORE_PID=$!

wait "$AUTODARTS_PID"
