# Autodarts 1.0.7 – Offline Calibration V10

V10 is a minimal follow-up to V9. The local calibration algorithm and the patched Autodarts binary are unchanged.

## What changed

V9 proved that the local calibration endpoint is reached and that Autodarts rejects the response because `calibration` was returned as an array. The observed Autodarts error was:

`json: cannot unmarshal array into Go struct field AutoCalibration.calibration of type map[string][][]float64`

V10 therefore changes only the response shape from:

```json
{"calibration": [[...], [...], [...]]}
```

to:

```json
{"calibration": {"0": [...], "1": [...], "2": [...]}}
```

The local detector, camera handling, patched binary, and test setup are otherwise unchanged.

## Test

```bash
cd ~/autodarts-offline-calibration-bundle-v10
./setup-test.sh
./start-autodarts-offline.sh
```

Wait until the board is stable, then press Auto Calibration once.

The important result is whether Autodarts accepts the local JSON response and continues to `Throw` instead of logging `Auto-calibration failed`.
