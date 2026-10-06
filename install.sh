#!/bin/bash

set -euo pipefail

REPO_DIR="/root/dans-playground"
DATA_DIR="/var/lib/dans-playground"
SYSTEMD_DIR="/etc/systemd/system"
AUTODARTS_CONFIG="$REPO_DIR/.config/autodarts/config.toml"
VENV_DIR="$REPO_DIR/dartbridge/venv"

log() {
    echo
    echo "============================================================"
    echo " $1"
    echo "============================================================"
}

if [ "$(id -u)" -ne 0 ]; then
    echo "FEHLER: install.sh muss als root ausgeführt werden."
    exit 1
fi

if [ ! -d "$REPO_DIR/.git" ]; then
    echo "FEHLER: $REPO_DIR ist kein Git-Repository."
    exit 1
fi

cd "$REPO_DIR"

log "Dan's Playground Installer"

echo "Repository: $REPO_DIR"
echo "Daten:      $DATA_DIR"

log "Installiere benötigte Systempakete"

apt-get update

DEBIAN_FRONTEND=noninteractive apt-get install -y \
    curl \
    git \
    python3 \
    python3-venv \
    python3-pip \
    ca-certificates

log "Erstelle persistentes Datenverzeichnis"

mkdir -p "$DATA_DIR"
chown root:root "$DATA_DIR"
chmod 755 "$DATA_DIR"

# board.json wird NICHT erstellt.
# Die Board-Identität entsteht erst bei der Provisionierung.

log "Prüfe Autodarts-Konfiguration"

mkdir -p "$REPO_DIR/.config/autodarts"

if [ ! -f "$AUTODARTS_CONFIG" ]; then

    cat > "$AUTODARTS_CONFIG" <<'CONFIG'
[auth]
board_id = ''
api_key = ''

[cam]
cams = ['/dev/video0', '/dev/video4', '/dev/video2']
width = 1280
height = 720
fps = 15
rotate_180 = [false, false, false]
auto_calibrate_on_start = false
auto_distortion = false

[motion]
stable_num_frames = 3
CONFIG

    echo "Autodarts-Konfiguration wurde angelegt."

else

    echo "Bestehende Autodarts-Konfiguration bleibt unverändert."

fi

chown root:root "$AUTODARTS_CONFIG"
chmod 600 "$AUTODARTS_CONFIG"

log "Richte Dart-Bridge Python-Umgebung ein"

if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/python" -m pip install --upgrade pip

"$VENV_DIR/bin/pip" install --upgrade \
    paho-mqtt \
    websocket-client

chown -R root:root "$VENV_DIR"

log "Setze Dateirechte"

chmod +x "$REPO_DIR/install.sh"
chmod +x "$REPO_DIR/update.sh"
chmod +x "$REPO_DIR/start-autodarts.sh"

chown root:root \
    "$REPO_DIR/install.sh" \
    "$REPO_DIR/update.sh" \
    "$REPO_DIR/start-autodarts.sh"

if [ -f "$REPO_DIR/.local/opt/autodarts/autodarts" ]; then
    chown root:root "$REPO_DIR/.local/opt/autodarts/autodarts"
    chmod 755 "$REPO_DIR/.local/opt/autodarts/autodarts"
fi

log "Installiere Agent-Konfiguration"

mkdir -p /etc/dans-playground
chown root:root /etc/dans-playground
chmod 755 /etc/dans-playground

if [ ! -f /etc/dans-playground/agent.env ]; then

    if [ -f "$REPO_DIR/etc/dans-playground/agent.env" ]; then

        cp "$REPO_DIR/etc/dans-playground/agent.env" \
           /etc/dans-playground/agent.env

    else

        echo "WARNUNG: agent.env fehlt im Repository."

    fi

else

    echo "Bestehende agent.env bleibt unverändert."

fi

if [ -f /etc/dans-playground/agent.env ]; then
    chown root:root /etc/dans-playground/agent.env
    chmod 600 /etc/dans-playground/agent.env
fi

log "Installiere systemd Services"

SYSTEMD_FILES=(
    "autodarts.service"
    "dans-playground-agent.service"
    "dans-playground-boardmanager.service"
    "dans-playground-bridge.service"
    "dans-playground-update.service"
)

for service in "${SYSTEMD_FILES[@]}"; do

    if [ ! -f "$REPO_DIR/systemd/$service" ]; then
        echo "FEHLER: systemd/$service fehlt."
        exit 1
    fi

    cp "$REPO_DIR/systemd/$service" \
       "$SYSTEMD_DIR/$service"

    chown root:root "$SYSTEMD_DIR/$service"
    chmod 644 "$SYSTEMD_DIR/$service"

done

log "Deaktiviere offiziellen Autodarts-Updater"

# Der offizielle Autodarts-Updater darf unsere
# eingefrorene Autodarts-Version 1.0.7 nicht aktualisieren.

systemctl disable --now autodartsupdater.service 2>/dev/null || true

log "Installiere Update-Timer"

cat > "$SYSTEMD_DIR/dans-playground-update.timer" <<'TIMER'
[Unit]
Description=Dan's Playground Automatic Update Check

[Timer]
OnBootSec=5min
OnUnitActiveSec=1h
Persistent=true

[Install]
WantedBy=timers.target
TIMER

chown root:root \
    "$SYSTEMD_DIR/dans-playground-update.timer"

chmod 644 \
    "$SYSTEMD_DIR/dans-playground-update.timer"

log "Lade systemd neu"

systemctl daemon-reload

log "Aktiviere Services"

systemctl enable \
    autodarts.service \
    dans-playground-agent.service \
    dans-playground-boardmanager.service \
    dans-playground-bridge.service

systemctl enable \
    dans-playground-update.timer

log "Starte Services"

start_if_needed() {
    local service="$1"

    if systemctl is-active --quiet "$service"; then
        log "$service läuft bereits."
    else
        log "Starte $service..."
        systemctl start "$service"
    fi
}

start_if_needed "dans-playground-boardmanager.service"
start_if_needed "dans-playground-agent.service"
start_if_needed "autodarts.service"
if systemctl is-active --quiet "dans-playground-bridge.service"; then
    log "dans-playground-bridge.service läuft bereits."
else
    log "Starte dans-playground-bridge.service im Hintergrund..."
    systemctl start --no-block "dans-playground-bridge.service"
fi
start_if_needed "dans-playground-update.timer"

log "Installation abgeschlossen"

echo
echo "============================================================"
echo " Status"
echo "============================================================"
echo

systemctl --no-pager --full status \
    dans-playground-boardmanager.service \
    dans-playground-agent.service \
    autodarts.service \
    dans-playground-bridge.service \
    dans-playground-update.timer \
    || true

echo
echo "============================================================"
echo " Wichtige Hinweise"
echo "============================================================"
echo
echo "board.json wurde NICHT erstellt oder verändert."
echo "Der offizielle Autodarts-Updater bleibt deaktiviert."
echo "Updates erfolgen ausschließlich über GitHub / update.sh."
echo

