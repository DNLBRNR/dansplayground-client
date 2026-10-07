#!/bin/bash
set -euo pipefail
BASE="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$BASE/config/autodarts" "$BASE/home" "$BASE/cache"

if [ ! -f "$HOME/manual-config.toml" ]; then
    echo "FEHLER: ~/manual-config.toml wurde nicht gefunden."
    exit 1
fi

cp -f "$HOME/manual-config.toml" "$BASE/good-calibration.toml"
cp -f "$HOME/manual-config.toml" "$BASE/config/autodarts/config.toml"
chmod 644 "$BASE/config/autodarts/config.toml"
rm -f "$BASE/captured-calibration-api.json"
chmod +x "$BASE/restore_calibration.py"

echo "V13: manuell funktionierende config geladen."
echo "Die echte API-Struktur wird erst nach dem Start von Autodarts per GET /config/calibration erfasst und bei unsicherer lokaler Erkennung als sicherer Fallback verwendet."
echo "Test-Konfiguration: $BASE/config/autodarts/config.toml"
echo "Start: $BASE/start-autodarts-offline.sh"
