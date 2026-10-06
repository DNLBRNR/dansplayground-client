#!/bin/bash

set -euo pipefail

REPO_DIR="/root/dans-playground"
DATA_DIR="/var/lib/dans-playground"
CONFIG_DIR="/etc/dans-playground"

SERVICES=(
    "dans-playground-bridge.service"
    "autodarts.service"
    "dans-playground-agent.service"
    "dans-playground-boardmanager.service"
    "dans-playground-update.service"
)

TIMER="dans-playground-update.timer"

echo
echo "============================================================"
echo " Dan's Playground Deinstaller"
echo "============================================================"
echo
echo "ACHTUNG!"
echo
echo "Diese Aktion entfernt die lokale Dan's Playground Installation."
echo
echo "Entfernt werden:"
echo "  - Dan's Playground Services"
echo "  - Update-Timer"
echo "  - /root/dans-playground"
echo "  - /var/lib/dans-playground"
echo "  - /etc/dans-playground"
echo
echo "Das GitHub-Repository wird NICHT verändert."
echo
echo "Die Deinstallation kann NICHT rückgängig gemacht werden."
echo

read -r -p "Wirklich deinstallieren? [yes/NO]: " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo
    echo "Deinstallation abgebrochen."
    exit 0
fi

echo
echo "Deinstallation wird gestartet..."
echo

echo "============================================================"
echo " Stoppe Services"
echo "============================================================"

for service in "${SERVICES[@]}"; do
    systemctl stop "$service" 2>/dev/null || true
done

echo
echo "============================================================"
echo " Deaktiviere Services"
echo "============================================================"

for service in "${SERVICES[@]}"; do
    systemctl disable "$service" 2>/dev/null || true
done

systemctl stop "$TIMER" 2>/dev/null || true
systemctl disable "$TIMER" 2>/dev/null || true

echo
echo "============================================================"
echo " Entferne systemd Dateien"
echo "============================================================"

rm -f /etc/systemd/system/autodarts.service
rm -f /etc/systemd/system/dans-playground-agent.service
rm -f /etc/systemd/system/dans-playground-boardmanager.service
rm -f /etc/systemd/system/dans-playground-bridge.service
rm -f /etc/systemd/system/dans-playground-update.service
rm -f /etc/systemd/system/dans-playground-update.timer

systemctl daemon-reload
systemctl reset-failed 2>/dev/null || true

echo
echo "============================================================"
echo " Entferne Dan's Playground Daten"
echo "============================================================"

rm -rf "$DATA_DIR"
rm -rf "$CONFIG_DIR"

echo
echo "============================================================"
echo " Entferne lokale Installation"
echo "============================================================"

rm -rf "$REPO_DIR"

echo
echo "============================================================"
echo " Deinstallation abgeschlossen"
echo "============================================================"
echo
echo "Dan's Playground wurde vollständig von diesem System entfernt."
echo
echo "Systempakete wurden NICHT entfernt."
echo "Der offizielle Autodarts-Updater wurde NICHT aktiviert."
echo
