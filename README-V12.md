# Autodarts Offline Calibration V12

V12 fixes the V11 safety-watcher endpoint bug.

Autodarts local API endpoints are under `/api`, so the watcher now uses:
- GET `/api/config/calibration`
- PUT `/api/config/calibration`

V11 incorrectly queried `/config/calibration`, so it never captured the known-good state. As a result its fallback had no saved state and returned HTTP 503.

V12 keeps the local detector and debug captures, but if detection is uncertain it returns the exact calibration object captured from the running Autodarts instance. It does not add extra fields to the JSON payload.

## Test

```bash
cd ~/autodarts-offline-calibration-bundle-v12
./setup-test.sh
./start-autodarts-offline.sh
```

Do not start `calibration_server_offline.py` separately.

Before pressing Auto Calibration, verify the terminal contains:

`Echte API-Kalibrierung gespeichert:`

Only then press Auto Calibration.
