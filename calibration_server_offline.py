#!/usr/bin/env python3
"""
Dan's Playground - V13 fully-local Autodarts 1.0.7 calibration service.

No Autodarts cloud request is made.

V13 important finding:
Autodarts 1.0.7 stores the classic per-camera calibration as FOUR image-space
points. The Board Manager UI labels these references 20-1, 6-10, 3-19, 11-14.
The patched binary still performs the actual homography calculation locally
when SetAutoCalibrationForCam() receives these points.

This service therefore does NOT try to invent a 3x3 matrix. It detects the
four outer-double-wire reference points in the camera image and returns the
four image coordinates in the shape expected by the multi-camera response.

The detector uses OpenCV only. It is intentionally conservative and writes a
visual debug image plus JSON diagnostics into CALIBRATION_STORE so a failed
attempt can be tuned without touching the binary again.
"""
from __future__ import annotations

import json
import math
import os
import re
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import cv2
import numpy as np

SINGLE_PORT = int(os.environ.get("CALIBRATION_SINGLE_PORT", "8082"))
MULTI_PORT = int(os.environ.get("CALIBRATION_MULTI_PORT", "8081"))
STORE = Path(os.environ.get("CALIBRATION_STORE", "/var/lib/dans-playground/calibration-cache"))
STORE.mkdir(parents=True, exist_ok=True)

# Autodarts Board Manager uses these four reference wires.
# Angle convention follows the board-manager SVG: 0° points right,
# 90° down in image coordinates, with the four boundaries at -9, 81, 171, 261°.
REF_ANGLES_DEG = [-9.0, 81.0, 171.0, 261.0]


def log(msg: str) -> None:
    print(f"[Offline Calibration V13] {msg}", flush=True)


def save_json(name: str, obj: Any) -> None:
    (STORE / name).write_text(
        json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def save_debug(name: str, image: np.ndarray) -> None:
    cv2.imwrite(str(STORE / name), image, [cv2.IMWRITE_JPEG_QUALITY, 92])


def load_image(body: bytes) -> np.ndarray | None:
    arr = np.frombuffer(body, dtype=np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def angle_diff(a: float, b: float) -> float:
    d = (a - b + 180.0) % 360.0 - 180.0
    return abs(d)


def detect_board(img: np.ndarray) -> tuple[float, float, float, dict[str, Any]] | None:
    """Detect board center/radius using multiple Hough scales and contour fallback."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (9, 9), 2.0)
    h, w = gray.shape
    min_dim = min(h, w)

    candidates: list[tuple[float, float, float, float]] = []
    for p2 in (55, 65, 75, 85, 95):
        circles = cv2.HoughCircles(
            gray, cv2.HOUGH_GRADIENT, dp=1.2, minDist=min_dim * 0.25,
            param1=120, param2=p2,
            minRadius=int(min_dim * 0.22), maxRadius=int(min_dim * 0.49)
        )
        if circles is None:
            continue
        for x, y, r in np.round(circles[0]).astype(float):
            if x < 0 or y < 0 or x >= w or y >= h:
                continue
            # Prefer circles with a center not too close to image edge.
            edge = min(x, y, w - x, h - y) / min_dim
            score = edge + 0.15 * (r / min_dim)
            candidates.append((score, x, y, r))

    if candidates:
        candidates.sort(reverse=True)
        _, x, y, r = candidates[0]
        return x, y, r, {"method": "hough", "candidates": len(candidates)}

    # Ellipse fallback from strong outer contours.
    edges = cv2.Canny(gray, 60, 150)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    best = None
    for c in contours:
        if len(c) < 40:
            continue
        area = cv2.contourArea(c)
        if area < (min_dim * min_dim * 0.12):
            continue
        peri = cv2.arcLength(c, True)
        if peri <= 0:
            continue
        circ = 4 * math.pi * area / (peri * peri)
        if circ < 0.35:
            continue
        try:
            (cx, cy), (a, b), ang = cv2.fitEllipse(c)
        except cv2.error:
            continue
        r = 0.25 * (a + b)
        if not (min_dim * 0.22 < r < min_dim * 0.50):
            continue
        score = area * max(circ, 0.01)
        if best is None or score > best[0]:
            best = (score, cx, cy, r, a, b, ang)
    if best:
        _, cx, cy, r, a, b, ang = best
        return cx, cy, r, {"method": "ellipse", "axes": [a, b], "angle": ang}
    return None


def detect_reference_points(img: np.ndarray) -> tuple[list[list[float]] | None, dict[str, Any], np.ndarray]:
    """
    Detect the four outer-double reference wire intersections.

    We search for radial wire/edge evidence in a broad annulus around the board,
    then choose the strongest angular evidence near the four known boundaries.
    The result is deliberately image-space pixel coordinates.
    """
    board = detect_board(img)
    dbg = img.copy()
    if board is None:
        return None, {"ok": False, "reason": "board_not_found"}, dbg

    cx, cy, r, board_meta = board
    cv2.circle(dbg, (round(cx), round(cy)), round(r), (255, 180, 0), 2)
    cv2.drawMarker(dbg, (round(cx), round(cy)), (255, 180, 0), cv2.MARKER_CROSS, 24, 2)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Work near the double ring where the four calibration intersections live.
    inner = max(8, int(r * 0.72))
    outer = max(inner + 5, int(r * 1.02))
    yy, xx = np.ogrid[:gray.shape[0], :gray.shape[1]]
    rr = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    ann = np.zeros_like(gray)
    ann[(rr >= inner) & (rr <= outer)] = gray[(rr >= inner) & (rr <= outer)]

    edges = cv2.Canny(ann, 45, 130)
    lines = cv2.HoughLinesP(
        edges, 1, np.pi / 1800.0, threshold=max(18, int(r * 0.10)),
        minLineLength=max(20, int(r * 0.20)), maxLineGap=max(4, int(r * 0.025))
    )

    angle_scores = np.zeros(3600, dtype=np.float64)
    radial_samples: list[tuple[float, float, float]] = []
    if lines is not None:
        for line in lines[:, 0]:
            x1, y1, x2, y2 = map(float, line)
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            length = math.hypot(x2 - x1, y2 - y1)
            a = math.degrees(math.atan2(my - cy, mx - cx)) % 360.0
            # Radial alignment: line direction should point approximately to center.
            da = math.degrees(math.atan2(y2 - y1, x2 - x1)) % 180.0
            radial = min((da - a) % 180.0, (a - da) % 180.0)
            radial = min(radial, 180.0 - radial)
            if radial > 25.0:
                continue
            weight = length * max(0.0, 1.0 - radial / 25.0)
            idx = int(round(a * 10)) % 3600
            angle_scores[idx] += weight
            radial_samples.append((a, length, radial))
            cv2.line(dbg, (round(x1), round(y1)), (round(x2), round(y2)), (0, 180, 255), 1)

    # Also score dark/bright edge energy at each angle directly.
    for deg in np.arange(0, 360, 0.5):
        a = math.radians(deg)
        vals = []
        for frac in np.linspace(0.82, 1.00, 25):
            x = int(round(cx + r * frac * math.cos(a)))
            y = int(round(cy + r * frac * math.sin(a)))
            if 1 <= x < gray.shape[1] - 1 and 1 <= y < gray.shape[0] - 1:
                vals.append(abs(float(int(gray[y, x + 1])) - float(int(gray[y, x - 1]))) +
                            abs(float(int(gray[y + 1, x])) - float(int(gray[y - 1, x]))))
        if vals:
            angle_scores[int(round(deg * 10)) % 3600] += np.percentile(vals, 85) * 0.8

    points: list[list[float]] = []
    chosen: list[dict[str, float]] = []
    for target in REF_ANGLES_DEG:
        # Smooth scores in ±2° around target and select strongest local maximum.
        candidates = []
        for step in np.arange(-4.0, 4.01, 0.1):
            a = (target + step) % 360.0
            idx = int(round(a * 10)) % 3600
            score = 0.0
            for k in range(-8, 9):
                score += angle_scores[(idx + k) % 3600]
            candidates.append((score, a))
        score, a = max(candidates)
        rad = math.radians(a)
        # Use the outer-double radius as the reference location.
        px = cx + r * 0.985 * math.cos(rad)
        py = cy + r * 0.985 * math.sin(rad)
        points.append([float(px), float(py)])
        chosen.append({"target_deg": target, "detected_deg": a, "score": float(score), "x": float(px), "y": float(py)})
        cv2.circle(dbg, (round(px), round(py)), 7, (0, 255, 0), 2)
        cv2.putText(dbg, f"{target:.0f}", (round(px) + 8, round(py) - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1, cv2.LINE_AA)

    # Reject obviously useless detections. This keeps Autodarts from accepting
    # random points if a camera frame does not actually contain the board.
    strengths = [x["score"] for x in chosen]
    spread = max(strengths) / max(min(strengths), 1e-6)
    ok = all(s > 5.0 for s in strengths) and spread < 12.0
    meta = {
        "ok": bool(ok),
        "board": {"cx": cx, "cy": cy, "radius": r, **board_meta},
        "reference_points": chosen,
        "line_count": 0 if lines is None else int(len(lines)),
        "score_spread": float(spread),
    }
    if not ok:
        meta["reason"] = "weak_or_inconsistent_reference_detection"
        return None, meta, dbg
    return points, meta, dbg


def identity_distortion(width: int, height: int) -> dict[str, Any]:
    f = float(max(width, height))
    return {
        "enabled": False,
        "K": [[f, 0.0, width / 2.0], [0.0, f, height / 2.0], [0.0, 0.0, 1.0]],
        "d": [0.0, 0.0, 0.0, 0.0],
        "alpha": 0.0,
        "width": width,
        "height": height,
        "error": 0.0,
    }


def load_known_good_calibration() -> dict[str, Any] | None:
    """Load the exact calibration object captured from Autodarts at startup."""
    path = Path(os.environ.get("GOOD_CALIBRATION_API", str(STORE.parent / "captured-calibration-api.json")))
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        cal = obj.get("calibration") if isinstance(obj, dict) else None
        if isinstance(cal, dict) and cal:
            return obj
    except Exception:
        pass
    return None


def make_fallback_response(width: int, height: int) -> dict[str, Any] | None:
    """Return the exact known-good API object instead of inventing calibration data."""
    return load_known_good_calibration()


def make_response(points: list[list[float]], width: int, height: int) -> dict[str, Any]:
    # IMPORTANT: calibration is the image-space four-point array used by the
    # v1 Board Manager. Do not replace this with a 3x3 matrix.
    return {
        "calibration": {"0": points, "1": points, "2": points},
        "distortion": [
            identity_distortion(width, height),
            identity_distortion(width, height),
            identity_distortion(width, height),
        ],
    }


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    mode = "multi"

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"[Offline Calibration V13/{self.mode}] " + fmt % args, flush=True)

    def do_GET(self) -> None:
        if self.path == "/health":
            data = b"Dan's Playground Calibration V13 OK\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        self.send_error(404)

    def do_POST(self) -> None:
        try:
            n = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            n = 0
        body = self.rfile.read(n)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        cam_hint = re.search(r"/(?:https?://[^/]+/)?(\d+)$", self.path)
        cam = cam_hint.group(1) if cam_hint else "multi"
        (STORE / f"request_{cam}_{stamp}.jpg").write_bytes(body)

        img = load_image(body)
        if img is None:
            self.send_error(400, "invalid JPEG")
            return
        h, w = img.shape[:2]
        points, meta, dbg = detect_reference_points(img)
        save_debug(f"debug_{cam}_{stamp}.jpg", dbg)
        save_json(f"diagnostics_{cam}_{stamp}.json", meta)

        if points is None:
            # V13 is deliberately fail-safe: never send a malformed/guessed
            # calibration just because the detector is uncertain. If the real
            # known-good API object has already been captured, return that exact
            # object so Auto Calibration can complete without destroying the
            # working manual calibration. The diagnostics remain on disk.
            response = make_fallback_response(w, h)
            if response is None:
                payload = json.dumps({"error": "local calibration unavailable", "diagnostics": meta}).encode()
                self.send_response(503)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                log(f"Kein known-good API-State vorhanden: {meta.get('reason')}")
                return
                        # Do not leak the private marker to Autodarts: remove it from the
            # wire response after storing the complete diagnostic locally.
            save_json(f"fallback_{cam}_{stamp}.json", response)
            response.pop("_dans_playground_v12", None)
            payload = json.dumps(response, separators=(",", ":")).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)
            log(f"Lokaler Detector unsicher ({meta.get('reason')}) -> sende exakt gespeicherten known-good API-State")
            return

        response = make_response(points, w, h)
        payload = json.dumps(response, separators=(",", ":")).encode()
        save_json(f"response_v12_{cam}.json", response)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)
        log(f"Lokale Kalibrierung erkannt: {points}")


def serve(port: int, mode: str) -> None:
    cls = type(f"{mode.title()}Handler", (Handler,), {"mode": mode})
    httpd = ThreadingHTTPServer(("127.0.0.1", port), cls)
    log(f"{mode} service listening on 127.0.0.1:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    import threading
    t = threading.Thread(target=serve, args=(SINGLE_PORT, "single"), daemon=True)
    t.start()
    serve(MULTI_PORT, "multi")
