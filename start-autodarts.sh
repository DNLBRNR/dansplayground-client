#!/bin/bash

# Autodarts starten
/home/board/.local/opt/autodarts/autodarts &
AUTODARTS_PID=$!

# Warten, bis die API verfügbar ist
echo "Warte auf Autodarts API..."

until curl -s http://localhost:3180/api/state >/dev/null 2>&1; do
    sleep 2
done

echo "Autodarts API ist verfügbar."

# Autodarts Board starten
curl -s -X PUT http://localhost:3180/api/start

echo
echo "Autodarts Board gestartet."

# Autodarts im Vordergrund weiterlaufen lassen
wait $AUTODARTS_PID
