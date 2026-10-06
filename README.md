# 🎯 Dan's Playground

Dan's Playground ist eine Plattform für Dart-Spiele mit Unterstützung für physische Dartboards über den Dan's Playground Board Agent.

Das Projekt ist für mehrere Benutzer und mehrere Dartboards ausgelegt. Ein Raspberry Pi übernimmt dabei die Verbindung zwischen dem physischen Dartboard und der Dan's Playground-Plattform.

---

## 🚀 Installation auf einem neuen Raspberry Pi

### Voraussetzungen

- Debian / Raspberry Pi OS 64-bit
- Internetverbindung
- SSH-Zugriff
- `sudo`-Rechte

### 1. Git installieren

Auf einem frisch installierten System zuerst Git installieren:

```bash
sudo apt update
sudo apt install -y git
```

### 2. Dan's Playground herunterladen

Das Repository ist öffentlich und kann direkt über HTTPS geklont werden:

```bash
sudo git clone https://github.com/DNLBRNR/dansplayground-client.git /root/dans-playground
```

### 3. Installation starten

```bash
sudo /root/dans-playground/install.sh
```

Der Installer übernimmt anschließend automatisch:

- benötigte Systempakete
- Python-Umgebung für die Dart Bridge
- benötigte Python-Pakete
- Dan's Playground Board Agent
- lokalen Board Manager
- Autodarts
- systemd Services
- automatischen GitHub-Updater
- Update-Timer

Die individuelle Board-Identität wird **nicht** im GitHub-Repository gespeichert.

---

## 🔄 Automatische Updates

Nach der Installation prüft Dan's Playground automatisch regelmäßig auf neue Versionen im GitHub-Repository.

Updates werden ausschließlich über:

```text
GitHub → update.sh
```

durchgeführt.

Der offizielle Autodarts-Updater bleibt deaktiviert.

---

## 🗑️ Deinstallation

Wenn Dan's Playground vollständig von einem Raspberry Pi entfernt werden soll:

```bash
sudo /root/dans-playground/uninstall.sh
```

Der Deinstaller fragt zur Sicherheit nach einer Bestätigung.

Entfernt werden unter anderem:

- Dan's Playground Services
- Update-Timer
- `/root/dans-playground`
- `/var/lib/dans-playground`
- `/etc/dans-playground`

Das GitHub-Repository selbst wird dabei **nicht** verändert.

---

## 📁 Wichtige Verzeichnisse

| Pfad | Beschreibung |
|---|---|
| `/root/dans-playground` | Lokale Installation |
| `/var/lib/dans-playground` | Persistente Board-Daten |
| `/etc/dans-playground` | Systemweite Konfiguration |
| `/var/lib/dans-playground/board.json` | Individuelle Board-Identität |

`board.json` wird bewusst nicht in GitHub gespeichert, da diese Datei die individuelle Identität des jeweiligen Boards enthält.

---

## 🧪 Test einer Neuinstallation

Für einen neuen Test-Pi reicht:

```bash
sudo apt update
sudo apt install -y git
sudo git clone https://github.com/DNLBRNR/dansplayground-client.git /root/dans-playground
sudo /root/dans-playground/install.sh
```

Damit lässt sich eine komplette Neuinstallation reproduzierbar testen.

---

## 📌 Projektstatus

Dan's Playground befindet sich aktuell in aktiver Entwicklung.

Die aktuelle Installation enthält unter anderem:

- Autodarts Board Software
- Dan's Playground Board Agent
- lokalen Board Manager
- Dart Bridge
- automatische GitHub-Updates
- Board-Provisionierung / Pairing

Weitere Funktionen wie Benutzerkonten, mehrere Boards und Online-Multiplayer sind Teil der weiteren Entwicklung.
