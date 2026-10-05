#!/usr/bin/env python3

import json
import os
import threading
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


CONFIG_FILE = Path("/etc/dans-playground/agent.env")
IDENTITY_FILE = Path("/var/lib/dans-playground/board.json")

HOST = "0.0.0.0"
PORT = 8080

PAIRING_REFRESH_CHECK_SECONDS = 30
PAIRING_REFRESH_BEFORE_SECONDS = 90

identity_lock = threading.Lock()


def load_env_file(path):
    values = {}

    if not path.exists():
        return values

    for line in path.read_text().splitlines():
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()

    return values


config = load_env_file(CONFIG_FILE)

SERVER_URL = config.get("DANS_PLAYGROUND_SERVER")


if not SERVER_URL:
    raise RuntimeError("DANS_PLAYGROUND_SERVER fehlt.")


def load_identity():
    if not IDENTITY_FILE.exists():
        return None

    try:
        return json.loads(
            IDENTITY_FILE.read_text(
                encoding="utf-8"
            )
        )
    except Exception as error:
        print(
            f"Fehler beim Lesen der Board-Identität: {error}"
        )
        return None


def save_identity(data):
    IDENTITY_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_file = IDENTITY_FILE.with_suffix(".tmp")

    temporary_file.write_text(
        json.dumps(data, indent=2),
        encoding="utf-8",
    )

    os.chmod(
        temporary_file,
        0o600,
    )

    temporary_file.replace(
        IDENTITY_FILE
    )

    os.chmod(
        IDENTITY_FILE,
        0o600,
    )


def get_identity():
    with identity_lock:
        return load_identity()


def update_identity(updates):
    with identity_lock:
        identity = load_identity()

        if identity is None:
            return None

        identity.update(updates)

        save_identity(identity)

        return identity


def provision_board():
    url = (
        SERVER_URL.rstrip("/")
        + "/api/boards/provision"
    )

    request = urllib.request.Request(
        url,
        method="POST",
        headers={
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=10,
        ) as response:
            body = response.read().decode(
                "utf-8"
            )

        data = json.loads(body)

    except urllib.error.HTTPError as error:
        body = error.read().decode(
            "utf-8",
            errors="replace",
        )

        raise RuntimeError(
            f"Backend HTTP {error.code}: {body}"
        )

    except Exception as error:
        raise RuntimeError(
            f"Provisioning fehlgeschlagen: {error}"
        )

    required = [
        "boardId",
        "deviceSecret",
        "pairingCode",
        "pairingCodeExpiresAt",
    ]

    for key in required:
        if key not in data:
            raise RuntimeError(
                f"Backend-Antwort enthält {key} nicht."
            )

    identity = {
        "boardId": data["boardId"],
        "deviceSecret": data["deviceSecret"],
        "pairingCode": data["pairingCode"],
        "pairingCodeExpiresAt": data[
            "pairingCodeExpiresAt"
        ],
        "provisionedAt": datetime.now(
            timezone.utc
        ).isoformat(),
        "paired": False,
    }

    save_identity(identity)

    print()
    print("========================================")
    print(" BOARD PROVISIONIERT")
    print("========================================")
    print(
        f"Board ID:     {identity['boardId']}"
    )
    print(
        f"Pairing-Code: {identity['pairingCode']}"
    )
    print(
        f"Gültig bis:   "
        f"{identity['pairingCodeExpiresAt']}"
    )
    print("========================================")
    print()

    return identity


def parse_expiry(value):
    if not isinstance(value, str) or not value:
        return None

    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except ValueError:
        return None


def refresh_pairing_code(identity):
    url = (
        SERVER_URL.rstrip("/")
        + "/api/boards/pairing-code"
    )

    data = json.dumps({
        "boardId": identity["boardId"],
        "deviceSecret": identity["deviceSecret"],
    }).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=10,
        ) as response:
            body = response.read().decode(
                "utf-8"
            )

        result = json.loads(body)

        required = [
            "pairingCode",
            "pairingCodeExpiresAt",
        ]

        for key in required:
            if key not in result:
                raise RuntimeError(
                    f"Backend-Antwort enthält {key} nicht."
                )

        updated = update_identity({
            "pairingCode": result["pairingCode"],
            "pairingCodeExpiresAt": result[
                "pairingCodeExpiresAt"
            ],
            "paired": False,
        })

        print(
            "Pairing-Code automatisch erneuert: "
            f"{updated['pairingCode'] if updated else 'unbekannt'}"
        )

        return updated

    except urllib.error.HTTPError as error:
        body = error.read().decode(
            "utf-8",
            errors="replace",
        )

        try:
            result = json.loads(body)
        except json.JSONDecodeError:
            result = {}

        if (
            error.code == 409
            and result.get("error")
            == "BOARD_ALREADY_PAIRED"
        ):
            updated = update_identity({
                "paired": True
            })

            print(
                "Board ist bereits gekoppelt. "
                "Pairing-Code-Refresh beendet."
            )

            return updated

        raise RuntimeError(
            "Pairing-Code-Refresh "
            f"Backend HTTP {error.code}: {body}"
        )

    except Exception as error:
        raise RuntimeError(
            f"Pairing-Code-Refresh fehlgeschlagen: {error}"
        )


def pairing_manager():
    print(
        "Pairing-Code-Manager gestartet."
    )

    while True:
        try:
            identity = get_identity()

            if identity is None:
                try:
                    provision_board()
                except Exception as error:
                    print(
                        "Automatische Provisionierung "
                        f"fehlgeschlagen: {error}"
                    )

                time.sleep(
                    PAIRING_REFRESH_CHECK_SECONDS
                )
                continue

            if identity.get("paired") is True:
                time.sleep(
                    PAIRING_REFRESH_CHECK_SECONDS
                )
                continue

            expiry = parse_expiry(
                identity.get(
                    "pairingCodeExpiresAt"
                )
            )

            if expiry is None:
                print(
                    "Pairing-Code-Ablaufdatum fehlt "
                    "oder ist ungültig. Erneuere Code."
                )

                try:
                    refresh_pairing_code(
                        identity
                    )
                except Exception as error:
                    print(
                        "Pairing-Code-Refresh "
                        f"fehlgeschlagen: {error}"
                    )

                time.sleep(
                    PAIRING_REFRESH_CHECK_SECONDS
                )
                continue

            seconds_remaining = (
                expiry
                - datetime.now(timezone.utc)
            ).total_seconds()

            if (
                seconds_remaining
                <= PAIRING_REFRESH_BEFORE_SECONDS
            ):
                try:
                    refresh_pairing_code(
                        identity
                    )
                except Exception as error:
                    print(
                        "Pairing-Code-Refresh "
                        f"fehlgeschlagen: {error}"
                    )

            time.sleep(
                PAIRING_REFRESH_CHECK_SECONDS
            )

        except Exception as error:
            print(
                f"Fehler im Pairing-Code-Manager: {error}"
            )

            time.sleep(
                PAIRING_REFRESH_CHECK_SECONDS
            )


def html_page(identity=None, error=None):
    if error:
        content = f"""
        <div class="error">
            <h2>Fehler</h2>
            <pre>{error}</pre>
        </div>
        """

    elif (
        identity
        and identity.get("paired") is True
    ):
        content = """
        <div class="success">
            <h2>Board gekoppelt</h2>

            <p>
                Dieses Board ist bereits mit einem
                Dan's Playground Konto verbunden.
            </p>

            <p class="small">
                Board-ID:<br>
                <span id="boardId">-</span>
            </p>
        </div>
        """

    elif identity:
        content = f"""
        <div class="success">
            <h2>Board bereit</h2>

            <p>
                Dieses Raspberry Pi Board wurde
                registriert.
            </p>

            <div class="code" id="pairingCode">
                {identity.get(
                    "pairingCode",
                    "--------"
                )}
            </div>

            <p>
                Gib diesen Code in deinem
                Dan's Playground Konto
                unter <b>Boards</b> ein.
            </p>

            <p class="small">
                Gültig bis:<br>
                <span id="expiresAt">
                    {identity.get(
                        "pairingCodeExpiresAt",
                        "-"
                    )}
                </span>
            </p>

            <p class="small">
                Board-ID:<br>
                <span id="boardId">
                    {identity.get(
                        "boardId",
                        "-"
                    )}
                </span>
            </p>
        </div>
        """

    else:
        content = """
        <div>
            <h2>Board wird eingerichtet</h2>

            <p>
                Dieses Raspberry Pi Board wird
                automatisch bei Dan's Playground
                registriert.
            </p>

            <p class="small">
                Die Seite aktualisiert sich
                automatisch.
            </p>
        </div>
        """

    polling_script = """
<script>
async function refreshStatus() {
    try {
        const response = await fetch('/status', {
            cache: 'no-store'
        });

        if (!response.ok) {
            return;
        }

        const data = await response.json();

        if (data.paired) {
            window.location.reload();
            return;
        }

        if (data.identity) {
            const pairingCode =
                document.getElementById(
                    'pairingCode'
                );

            const expiresAt =
                document.getElementById(
                    'expiresAt'
                );

            const boardId =
                document.getElementById(
                    'boardId'
                );

            if (pairingCode) {
                pairingCode.textContent =
                    data.identity.pairingCode
                    || '--------';
            }

            if (expiresAt) {
                expiresAt.textContent =
                    data.identity
                        .pairingCodeExpiresAt
                    || '-';
            }

            if (boardId) {
                boardId.textContent =
                    data.identity.boardId
                    || '-';
            }
        } else {
            window.location.reload();
        }

    } catch (error) {
        console.log(
            'Status-Update fehlgeschlagen'
        );
    }
}

setInterval(
    refreshStatus,
    10000
);
</script>
"""

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta
    name="viewport"
    content="width=device-width,
    initial-scale=1.0"
>
<meta
    http-equiv="Cache-Control"
    content="no-store"
>

<title>Dan's Playground</title>

<style>

body {{
    margin: 0;
    background: #111;
    color: #fff;
    font-family: Arial, sans-serif;
}}

.container {{
    max-width: 700px;
    margin: 80px auto;
    padding: 40px;
    text-align: center;
}}

h1 {{
    font-size: 42px;
    margin-bottom: 10px;
}}

h2 {{
    font-size: 28px;
}}

p {{
    font-size: 18px;
    line-height: 1.5;
}}

.code {{
    margin: 35px 0;
    padding: 25px;
    background: #222;
    border-radius: 15px;
    font-size: 42px;
    font-weight: bold;
    letter-spacing: 5px;
}}

.success {{
    margin-top: 30px;
}}

.error {{
    background: #351515;
    padding: 25px;
    border-radius: 10px;
}}

pre {{
    white-space: pre-wrap;
}}

.small {{
    font-size: 14px;
    opacity: 0.7;
}}

</style>
</head>

<body>

<div class="container">

<h1>🎯 Dan's Playground</h1>

{content}

</div>

{polling_script}

</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        print(
            f"{self.client_address[0]} - "
            f"{format % args}"
        )

    def send_html(self, content, status=200):
        data = content.encode("utf-8")

        self.send_response(status)

        self.send_header(
            "Content-Type",
            "text/html; charset=utf-8",
        )

        self.send_header(
            "Cache-Control",
            "no-store",
        )

        self.send_header(
            "X-Content-Type-Options",
            "nosniff",
        )

        self.send_header(
            "Content-Length",
            str(len(data)),
        )

        self.end_headers()

        self.wfile.write(data)

    def send_json(self, data, status=200):
        body = json.dumps(data).encode(
            "utf-8"
        )

        self.send_response(status)

        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8",
        )

        self.send_header(
            "Cache-Control",
            "no-store",
        )

        self.send_header(
            "Content-Length",
            str(len(body)),
        )

        self.end_headers()

        self.wfile.write(body)

    def do_GET(self):

        if self.path == "/":
            identity = get_identity()

            self.send_html(
                html_page(identity)
            )

            return

        if self.path == "/health":
            self.send_json({
                "status": "ok"
            })

            return

        if self.path == "/status":
            identity = get_identity()

            if identity is None:
                self.send_json({
                    "paired": False,
                    "identity": None,
                })

                return

            safe_identity = {
                "boardId": identity.get(
                    "boardId"
                ),
                "pairingCode": identity.get(
                    "pairingCode"
                ),
                "pairingCodeExpiresAt":
                    identity.get(
                        "pairingCodeExpiresAt"
                    ),
            }

            self.send_json({
                "paired":
                    identity.get("paired")
                    is True,
                "identity":
                    safe_identity,
            })

            return

        self.send_error(404)

    def do_POST(self):

        if self.path != "/provision":
            self.send_error(404)
            return

        existing = get_identity()

        if existing:
            self.send_html(
                html_page(existing)
            )

            return

        try:
            identity = provision_board()

            self.send_html(
                html_page(identity)
            )

        except Exception as error:

            print(
                f"Provisioning-Fehler: {error}"
            )

            self.send_html(
                html_page(
                    error=str(error)
                ),
                status=500,
            )


def main():

    identity = get_identity()

    if identity:
        print(
            f"Board bereits provisioniert: "
            f"{identity['boardId']}"
        )
    else:
        print(
            "Board noch nicht provisioniert. "
            "Automatische Provisionierung "
            "wird gestartet."
        )

    manager_thread = threading.Thread(
        target=pairing_manager,
        name="pairing-manager",
        daemon=True,
    )

    manager_thread.start()

    server = HTTPServer(
        (HOST, PORT),
        Handler,
    )

    print(
        f"Board Agent läuft auf "
        f"http://0.0.0.0:{PORT}"
    )

    server.serve_forever()


if __name__ == "__main__":
    main()
