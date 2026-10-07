#!/usr/bin/env python3
"""V13: capture the real Autodarts calibration API object, then restore it.

The important difference from V8 is that the known-good value is NOT
constructed from config.toml. We first ask the running Autodarts process for
GET /api/config/calibration while the manually calibrated state is active, and
save that exact JSON object. During Auto Calibration we watch the same
endpoint. If Autodarts changes it, we PUT the exact previously captured
object back through the same API.
"""
from __future__ import annotations
import json, os, time, urllib.error, urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent
API = os.environ.get("AUTODARTS_API", "http://127.0.0.1:3180")
POLL = float(os.environ.get("CALIBRATION_RESTORE_POLL", "0.15"))
CAPTURE = BASE / "captured-calibration-api.json"


def get_calibration():
    req = urllib.request.Request(API + "/api/config/calibration", method="GET")
    with urllib.request.urlopen(req, timeout=1.5) as r:
        raw = r.read().decode("utf-8")
        return json.loads(raw), r.status


def put_calibration(value):
    body = json.dumps(value, separators=(",", ":")).encode("utf-8")
    req = urllib.request.Request(
        API + "/api/config/calibration", data=body, method="PUT",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=2.5) as r:
        return r.status, r.read().decode("utf-8", errors="replace")


def norm(v):
    return json.dumps(v, sort_keys=True, separators=(",", ":"))


def wait_for_api():
    while True:
        try:
            value, status = get_calibration()
            print(f"[Dan's Playground V13] Calibration-API erreichbar (HTTP {status}).", flush=True)
            return value, status
        except Exception:
            time.sleep(0.5)


def main():
    print(f"[Dan's Playground V13] Echter API-Kalibrierungswächter: {API}", flush=True)
    print("[Dan's Playground V13] Warte auf Autodarts und lese GET /api/config/calibration ...", flush=True)
    good, _ = wait_for_api()

    # This is the authoritative known-good state: exactly what the running
    # Autodarts process exposes after loading the manually calibrated config.
    CAPTURE.write_text(json.dumps(good, indent=2), encoding="utf-8")
    good_norm = norm(good)
    print(f"[Dan's Playground V13] Echte API-Kalibrierung gespeichert: {CAPTURE}", flush=True)
    print("[Dan's Playground V13] Warte jetzt auf Änderungen durch Auto Calibration ...", flush=True)

    last_bad = None
    while True:
        try:
            current, _ = get_calibration()
            cur_norm = norm(current)
            if cur_norm == good_norm:
                last_bad = None
                time.sleep(POLL)
                continue

            if cur_norm != last_bad:
                print("[Dan's Playground V13] Auto Calibration hat den API-Kalibrierzustand verändert.", flush=True)
                print("[Dan's Playground V13] Stelle exakt den zuvor per GET gelesenen Zustand wieder her ...", flush=True)
                try:
                    status, body = put_calibration(good)
                    print(f"[Dan's Playground V13] PUT /api/config/calibration -> HTTP {status}", flush=True)
                    if body.strip():
                        print(f"[Dan's Playground V13] Antwort: {body[:500]}", flush=True)
                except Exception as exc:
                    print(f"[Dan's Playground V13] PUT fehlgeschlagen: {exc}", flush=True)
                last_bad = cur_norm
                time.sleep(0.25)
            else:
                time.sleep(POLL)
        except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError, OSError):
            time.sleep(0.5)


if __name__ == "__main__":
    main()
