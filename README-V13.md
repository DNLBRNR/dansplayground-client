# Autodarts Offline Calibration V13

## Purpose
V13 is a safety/diagnostic test for the offline calibration path.

The previous V12 test contained a Python watcher bug: `wait_for_api()` returned one value while `main()` tried to unpack two values. The watcher therefore crashed before saving the known-good calibration state.

V13 fixes that bug.

## Safe fallback
The watcher captures the exact JSON returned by:

`GET http://127.0.0.1:3180/api/config/calibration`

while the manually working calibration is loaded.

If local reference detection is uncertain, the calibration proxy returns that exact captured JSON object with HTTP 200 instead of sending 503. The goal is to prevent an unsuccessful local detector from replacing the working manual calibration.

## Test

```bash
cd ~/autodarts-offline-calibration-bundle-v13
./setup-test.sh
./start-autodarts-offline.sh
```

Do not start `calibration_server_offline.py` separately.

Before pressing Auto Calibration, verify that the terminal prints:

`Echte API-Kalibrierung gespeichert:`

Then press Auto Calibration once.

Useful artifacts are written into the bundle directory:
- `captured-calibration-api.json`
- `cache/` request/debug/diagnostic files

The production Autodarts binary is not modified by this test bundle.
