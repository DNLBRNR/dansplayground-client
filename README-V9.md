# Autodarts Offline Calibration V9

V9 korrigiert den Fehler von V8: Die bekannte gute Kalibrierung wird NICHT aus
`config.toml` in ein geratenes JSON-Format umgebaut.

Stattdessen startet V9 Autodarts zuerst mit der nachweislich funktionierenden
manuellen `~/manual-config.toml`. Danach liest V9 die **echte Antwort** von
`GET http://127.0.0.1:3180/config/calibration` aus dem laufenden Autodarts-
Prozess und speichert exakt dieses JSON-Objekt.

Wenn anschließend `Auto Calibration` den API-Zustand verändert, sendet V9
exakt dieses zuvor gelesene Objekt per `PUT /config/calibration` zurück.

## Test

```bash
cd /home/dan
tar -xzf autodarts-offline-calibration-bundle-v9.tar.gz
cd autodarts-offline-calibration-bundle-v9
./setup-test.sh
./start-autodarts-offline.sh
```

Danach **keine Punkte manuell setzen**. Auto Calibration starten und den
Terminal-Output beobachten.

Erwartet wird ungefähr:

```text
[Dan's Playground V9] Calibration-API erreichbar (HTTP 200).
[Dan's Playground V9] Echte API-Kalibrierung gespeichert: .../captured-calibration-api.json
[Dan's Playground V9] Auto Calibration hat den API-Kalibrierzustand verändert.
[Dan's Playground V9] Stelle exakt den zuvor per GET gelesenen Zustand wieder her ...
[Dan's Playground V9] PUT /config/calibration -> HTTP 200
```

Danach prüfen: Status `Throw` und Dart-Erkennung.

Produktionsinstallation unter `/root/dans-playground` wird nicht verändert.
