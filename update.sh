#!/bin/bash

set -euo pipefail

REPO_DIR="/root/dans-playground"
REMOTE="origin"
BRANCH="main"

AUTODARTS_CONFIG="$REPO_DIR/.config/autodarts/config.toml"
AUTODARTS_CONFIG_BACKUP="/tmp/dans-playground-autodarts-config.toml"

SERVICES=(
    "autodarts.service"
    "dans-playground-boardmanager.service"
    "dans-playground-agent.service"
    "dans-playground-bridge.service"
)

log() {
    echo "[Dan's Playground Update] $1"
}

cd "$REPO_DIR"

log "Prüfe GitHub auf Updates..."

git fetch "$REMOTE" "$BRANCH"

LOCAL_COMMIT="$(git rev-parse HEAD)"
REMOTE_COMMIT="$(git rev-parse "$REMOTE/$BRANCH")"

if [ "$LOCAL_COMMIT" = "$REMOTE_COMMIT" ]; then
    log "Bereits aktuell."
    exit 0
fi

log "Neue Version gefunden."
log "Lokal : $LOCAL_COMMIT"
log "GitHub: $REMOTE_COMMIT"

log "Stoppe Dan's Playground Services..."

for service in "${SERVICES[@]}"; do
    systemctl stop "$service" 2>/dev/null || true
done

log "Sichere lokale Autodarts-Konfiguration..."

if [ -f "$AUTODARTS_CONFIG" ]; then
    cp -p "$AUTODARTS_CONFIG" "$AUTODARTS_CONFIG_BACKUP"
fi

log "Aktualisiere lokalen Softwarestand..."

git reset --hard "$REMOTE/$BRANCH"

log "Stelle lokale Autodarts-Konfiguration wieder her..."

if [ -f "$AUTODARTS_CONFIG_BACKUP" ]; then
    cp -p "$AUTODARTS_CONFIG_BACKUP" "$AUTODARTS_CONFIG"
    rm -f "$AUTODARTS_CONFIG_BACKUP"
fi

chown board:board "$AUTODARTS_CONFIG"
chmod 600 "$AUTODARTS_CONFIG"

log "Neuer Stand:"
git rev-parse HEAD

log "Starte Dan's Playground Services..."

for service in "${SERVICES[@]}"; do
    systemctl start --no-block "$service" || true
done

log "Update erfolgreich abgeschlossen."
