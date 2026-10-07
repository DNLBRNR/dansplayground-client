# Dan's Playground – Autodarts offline calibration V11

V11 is a **safe diagnostic build** based on V10.

## What changed
- The V10 JSON structure fix remains.
- The local detector now always saves the incoming JPEG, debug image and diagnostics.
- If local reference detection is weak/inconsistent, V11 does **not** return HTTP 422.
- Instead it returns the exact `/config/calibration` object captured from the running Autodarts instance before calibration.
- This prevents a failed local detector from causing Autodarts to throw away the working manual calibration.
- The fallback response is stored locally for inspection.

## Important
The fallback is intentional. V11 first answers the question: **can we make Auto Calibration complete without losing the known-good calibration?**
Only after that should we enable/replace the local detector output.

The modified Autodarts binary is unchanged from V10.
