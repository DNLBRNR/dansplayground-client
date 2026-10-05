#!/usr/bin/env python3

import json
import time
import threading
from datetime import datetime, timezone
from pathlib import Path
import websocket


# ============================================================
# KONFIGURATION
# ============================================================

AUTODARTS_WS = "ws://localhost:3180/api/events?type=state"

BOARD_IDENTITY_FILE = Path(
    "/var/lib/dans-playground/board.json"
)

AGENT_CONFIG_FILE = Path(
    "/etc/dans-playground/agent.env"
)

HEARTBEAT_INTERVAL = 10
RECONNECT_INTERVAL = 5


# ============================================================
# ENVIRONMENT DATEI
# ============================================================

def load_env_file(path):
    values = {}

    if not path.exists():
        return values

    for line in path.read_text(
        encoding="utf-8"
    ).splitlines():

        line = line.strip()

        if (
            not line
            or line.startswith("#")
            or "=" not in line
        ):
            continue

        key, value = line.split("=", 1)

        values[key.strip()] = value.strip()

    return values


# ============================================================
# BOARD IDENTITÄT
# ============================================================

def load_board_identity():

    if not BOARD_IDENTITY_FILE.exists():
        raise RuntimeError(
            f"Board-Identität fehlt: "
            f"{BOARD_IDENTITY_FILE}"
        )

    try:

        data = json.loads(
            BOARD_IDENTITY_FILE.read_text(
                encoding="utf-8"
            )
        )

    except Exception as error:

        raise RuntimeError(
            "Board-Identität kann nicht gelesen werden: "
            f"{error}"
        ) from error

    board_id = data.get("boardId")
    device_secret = data.get("deviceSecret")

    if (
        not isinstance(board_id, str)
        or not board_id
    ):
        raise RuntimeError(
            "boardId fehlt in board.json."
        )

    if (
        not isinstance(device_secret, str)
        or not device_secret
    ):
        raise RuntimeError(
            "deviceSecret fehlt in board.json."
        )

    return board_id, device_secret


# ============================================================
# PLAYGROUND KONFIGURATION
# ============================================================

agent_config = load_env_file(
    AGENT_CONFIG_FILE
)

PLAYGROUND_SERVER = agent_config.get(
    "DANS_PLAYGROUND_SERVER"
)

if not PLAYGROUND_SERVER:

    raise RuntimeError(
        "DANS_PLAYGROUND_SERVER fehlt in "
        f"{AGENT_CONFIG_FILE}"
    )

PLAYGROUND_SERVER = PLAYGROUND_SERVER.rstrip("/")


if PLAYGROUND_SERVER.startswith("https://"):

    PLAYGROUND_WS = (
        "wss://"
        + PLAYGROUND_SERVER[len("https://"):]
        + "/board"
    )

elif PLAYGROUND_SERVER.startswith("http://"):

    # Lokale Entwicklungsumgebung:
    #
    # HTTP:
    #   :3000
    #
    # WebSocket:
    #   :3001

    host = PLAYGROUND_SERVER[
        len("http://"):
    ]

    if host.endswith(":3000"):

        host = (
            host[:-5]
            + ":3001"
        )

    PLAYGROUND_WS = (
        "ws://"
        + host
        + "/board"
    )

else:

    raise RuntimeError(
        "DANS_PLAYGROUND_SERVER muss mit "
        "http:// oder https:// beginnen."
    )


# ============================================================
# BOARD IDENTITÄT LADEN
# ============================================================

BOARD_ID, DEVICE_SECRET = load_board_identity()


# ============================================================
# STATUS
# ============================================================

autodarts_connected = False
autodarts_running = False

board_connected = False
board_socket = None


# ============================================================
# ZEIT
# ============================================================

def current_timestamp():

    return datetime.now(
        timezone.utc
    ).isoformat()


# ============================================================
# PLAYGROUND SENDEN
# ============================================================

def send_to_playground(payload):

    global board_socket

    socket = board_socket

    if (
        socket is None
        or not board_connected
    ):
        return False

    try:

        socket.send(
            json.dumps(
                payload,
                separators=(",", ":"),
            )
        )

        return True

    except Exception as error:

        print(
            "⚠️ Playground WebSocket Fehler: "
            f"{error}"
        )

        return False


# ============================================================
# BOARD STATUS
# ============================================================

def board_status_payload():

    return {
        "type": "board_status",
        "boardId": BOARD_ID,
        "timestamp": current_timestamp(),
        "autodartsConnected":
            autodarts_connected,
        "autodartsRunning":
            autodarts_running,
    }


def publish_status():

    if send_to_playground(
        board_status_payload()
    ):

        print(
            "📡 Status → Playground "
            f"(connected={autodarts_connected}, "
            f"running={autodarts_running})"
        )


# ============================================================
# HEARTBEAT
# ============================================================

def heartbeat_loop():

    while True:

        if board_connected:
            publish_status()

        time.sleep(
            HEARTBEAT_INTERVAL
        )


# ============================================================
# SCORE BERECHNEN
# ============================================================

def calculate_score(segment):

    number = segment.get(
        "number",
        0
    )

    multiplier = segment.get(
        "multiplier",
        0
    )

    if multiplier == 0:
        return 0

    if number == 25:

        return (
            25
            if multiplier == 1
            else 50
        )

    return number * multiplier


# ============================================================
# DART EVENT
# ============================================================

def process_event(message):

    global autodarts_running

    try:

        event = json.loads(
            message
        )

    except json.JSONDecodeError:

        print(
            "⚠️ Ungültige JSON-Nachricht "
            "von Autodarts"
        )

        return

    if event.get("type") != "state":
        return

    data = event.get(
        "data",
        {}
    )

    autodarts_running = data.get(
        "running",
        False
    )

    if data.get("event") != "Throw detected":
        return

    throws = data.get(
        "throws",
        []
    )

    if not throws:
        return

    dart = throws[-1]

    segment = dart.get(
        "segment",
        {}
    )

    coords = dart.get(
        "coords",
        {}
    )

    number = segment.get(
        "number",
        0
    )

    multiplier = segment.get(
        "multiplier",
        0
    )

    segment_name = segment.get(
        "name",
        ""
    )

    bed = segment.get(
        "bed",
        ""
    )

    x = coords.get("x")
    y = coords.get("y")

    score = calculate_score(
        segment
    )

    throw_number = data.get(
        "numThrows",
        0
    )

    timestamp = current_timestamp()

    dart_event = {

        "type": "dart",

        "boardId":
            BOARD_ID,

        "timestamp":
            timestamp,

        "throwNumber":
            throw_number,

        "number":
            number,

        "multiplier":
            multiplier,

        "segment":
            segment_name,

        "bed":
            bed,

        "score":
            score,

        "x":
            x,

        "y":
            y,
    }

    print()

    print(
        "=" * 60
    )

    print(
        "🎯 DART DETECTED"
    )

    print(
        "=" * 60
    )

    print(
        f"Board:       {BOARD_ID}"
    )

    print(
        f"Wurf:        {throw_number}"
    )

    print(
        f"Segment:     {segment_name}"
    )

    print(
        f"Number:      {number}"
    )

    print(
        f"Multiplier:  {multiplier}"
    )

    print(
        f"Bed:         {bed}"
    )

    print(
        f"Score:       {score}"
    )

    print(
        f"X:           {x}"
    )

    print(
        f"Y:           {y}"
    )

    print(
        "Transport:   WebSocket "
        "→ Dan's Playground"
    )

    print(
        "=" * 60
    )

    if send_to_playground(
        dart_event
    ):

        print(
            "📡 Dart → Dan's Playground "
            "übertragen"
        )

    else:

        print(
            "⚠️ Dart konnte nicht "
            "übertragen werden"
        )


# ============================================================
# PLAYGROUND CONNECTION
# ============================================================

def connect_playground():

    global board_connected
    global board_socket

    while True:

        socket = None

        try:

            print()

            print(
                "Verbinde mit Dan's Playground: "
                f"{PLAYGROUND_WS}"
            )

            # ------------------------------------------------
            # Verbindung herstellen
            # ------------------------------------------------

            socket = websocket.create_connection(
                PLAYGROUND_WS,
                timeout=10,
            )

            # ------------------------------------------------
            # WICHTIG:
            #
            # Der initiale Timeout von 10 Sekunden wird
            # nach erfolgreicher Verbindung entfernt.
            #
            # Dadurch führt ein recv() ohne neue
            # Server-Nachricht NICHT mehr nach 10 Sekunden
            # zu "Connection timed out".
            # ------------------------------------------------

            socket.settimeout(None)

            # ------------------------------------------------
            # Board authentifizieren
            # ------------------------------------------------

            socket.send(
                json.dumps(
                    {
                        "type":
                            "authenticate",

                        "boardId":
                            BOARD_ID,

                        "deviceSecret":
                            DEVICE_SECRET,
                    },
                    separators=(",", ":"),
                )
            )

            # ------------------------------------------------
            # Authentifizierungsantwort
            # ------------------------------------------------

            raw_response = socket.recv()

            if raw_response is None:

                raise ConnectionError(
                    "Playground-Verbindung "
                    "geschlossen"
                )

            response = json.loads(
                raw_response
            )

            if (
                response.get("type")
                != "board_auth"
                or
                response.get("status")
                != "authenticated"
            ):

                raise ConnectionError(
                    "Board-Authentifizierung "
                    f"abgelehnt: {response}"
                )

            # ------------------------------------------------
            # Verbindung als aktiv markieren
            # ------------------------------------------------

            board_socket = socket
            board_connected = True

            print(
                "✅ Mit Dan's Playground verbunden!"
            )

            print(
                f"   Board ID: {BOARD_ID}"
            )

            # ------------------------------------------------
            # Status sofort senden
            # ------------------------------------------------

            publish_status()

            # ------------------------------------------------
            # Auf Server-Nachrichten warten
            # ------------------------------------------------

            while True:

                message = socket.recv()

                if message is None:

                    raise ConnectionError(
                        "Playground WebSocket "
                        "geschlossen"
                    )

                try:

                    incoming = json.loads(
                        message
                    )

                    print(
                        "📥 Playground → Board: "
                        f"{incoming}"
                    )

                except json.JSONDecodeError:

                    print(
                        "⚠️ Ungültige Nachricht "
                        "vom Playground"
                    )

        except KeyboardInterrupt:

            break

        except Exception as error:

            print(
                "⚠️ Playground-Verbindung "
                f"verloren: {error}"
            )

        finally:

            board_connected = False

            if board_socket is socket:
                board_socket = None

            if socket is not None:

                try:

                    socket.close()

                except Exception:
                    pass

        print(
            "🔄 Neuer Playground-"
            "Verbindungsversuch in "
            f"{RECONNECT_INTERVAL} Sekunden..."
        )

        time.sleep(
            RECONNECT_INTERVAL
        )


# ============================================================
# AUTODARTS CONNECTION
# ============================================================

def connect_autodarts():

    global autodarts_connected
    global autodarts_running

    while True:

        try:

            print()

            print(
                "Verbinde mit Autodarts: "
                f"{AUTODARTS_WS}"
            )

            ws = websocket.create_connection(
                AUTODARTS_WS,
                timeout=10,
            )

            # Auch hier den Read-Timeout nach
            # erfolgreicher Verbindung entfernen.

            ws.settimeout(None)

            autodarts_connected = True

            print(
                "✅ Mit Autodarts verbunden!"
            )

            publish_status()

            while True:

                message = ws.recv()

                if message is None:

                    raise ConnectionError(
                        "Autodarts WebSocket "
                        "geschlossen"
                    )

                process_event(
                    message
                )

        except KeyboardInterrupt:

            print(
                "Bridge beendet."
            )

            break

        except Exception as error:

            autodarts_connected = False
            autodarts_running = False

            publish_status()

            print(
                "⚠️ Autodarts-Verbindung "
                f"verloren: {error}"
            )

            print(
                "🔄 Neuer Verbindungsversuch "
                "in 3 Sekunden..."
            )

            time.sleep(3)


# ============================================================
# TEST DART
# ============================================================

def simulate_test_dart():

    print()

    print(
        "=" * 60
    )

    print(
        "           TEST DART"
    )

    print(
        "=" * 60
    )

    print()

    test_event = {
        "type": "state",

        "data": {
            "connected": True,

            "running": True,

            "status": "Throw",

            "event": "Throw detected",

            "numThrows": 1,

            "throws": [
                {
                    "segment": {
                        "name": "S20",
                        "number": 20,
                        "bed": "SingleInner",
                        "multiplier": 1,
                    },

                    "coords": {
                        "x": -0.0206811775,
                        "y": 0.2847473705,
                    },
                }
            ],
        },
    }

    print(
        "Simuliere:"
    )

    print(
        "  Segment: S20"
    )

    print(
        "  Score:   20"
    )

    print(
        "  X:       -0.0206811775"
    )

    print(
        "  Y:        0.2847473705"
    )

    print()

    # Wir schicken den Test-Dart absichtlich
    # durch denselben Weg wie einen echten
    # Autodarts-Wurf.

    process_event(
        json.dumps(
            test_event
        )
    )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    import sys

    # ========================================================
    # TEST-MODUS
    # ========================================================

    if "--test-dart" in sys.argv:

        print()

        print(
            "=" * 60
        )

        print(
            "           DART BRIDGE TEST"
        )

        print(
            "=" * 60
        )

        print()

        print(
            f"Board ID:       {BOARD_ID}"
        )

        print(
            "Device Secret:  geladen aus board.json"
        )

        print(
            f"Playground:     {PLAYGROUND_WS}"
        )

        print()

        # ----------------------------------------------------
        # Playground-Verbindung starten
        # ----------------------------------------------------

        playground_thread = threading.Thread(
            target=connect_playground,
            daemon=True,
        )

        playground_thread.start()

        # ----------------------------------------------------
        # Warten, bis die Verbindung wirklich
        # authentifiziert wurde.
        #
        # Maximal 10 Sekunden.
        # ----------------------------------------------------

        print(
            "⏳ Warte auf Playground-Verbindung..."
        )

        deadline = time.time() + 10

        while (
            not board_connected
            and time.time() < deadline
        ):

            time.sleep(0.1)

        # ----------------------------------------------------
        # Keine Verbindung?
        # ----------------------------------------------------

        if not board_connected:

            print()

            print(
                "❌ Playground konnte für den "
                "Test nicht verbunden werden."
            )

            print()

            sys.exit(1)

        # ----------------------------------------------------
        # Test-Dart senden
        # ----------------------------------------------------

        print()

        print(
            "✅ Playground verbunden."
        )

        print(
            "🎯 Sende Test-Dart..."
        )

        simulate_test_dart()

        # ----------------------------------------------------
        # Kurz offen lassen, damit der Versand
        # sicher abgeschlossen werden kann.
        # ----------------------------------------------------

        time.sleep(1)

        print()

        print(
            "=" * 60
        )

        print(
            "           TEST BEENDET"
        )

        print(
            "=" * 60
        )

        print()

        sys.exit(0)

    # ========================================================
    # NORMALER START
    # ========================================================

    print()

    print(
        "=" * 60
    )

    print(
        "           DART BRIDGE"
    )

    print(
        "=" * 60
    )

    print()

    print(
        f"Board ID:       {BOARD_ID}"
    )

    print(
        "Device Secret:  geladen aus board.json"
    )

    print(
        f"Playground:     {PLAYGROUND_WS}"
    )

    print()

    # --------------------------------------------------------
    # Playground-Verbindung
    # --------------------------------------------------------

    playground_thread = threading.Thread(
        target=connect_playground,
        daemon=True,
    )

    playground_thread.start()

    # --------------------------------------------------------
    # Heartbeat
    # --------------------------------------------------------

    heartbeat_thread = threading.Thread(
        target=heartbeat_loop,
        daemon=True,
    )

    heartbeat_thread.start()

    print(
        "📡 Board-Heartbeat aktiv "
        f"(alle {HEARTBEAT_INTERVAL} Sekunden)"
    )

    # --------------------------------------------------------
    # Autodarts
    # --------------------------------------------------------

    connect_autodarts()
