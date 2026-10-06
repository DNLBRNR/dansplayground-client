# 🎯 Dan's Playground

Dan's Playground is a platform for dart games with support for physical dartboards through the Dan's Playground Board Agent.

The project is designed for multiple users and multiple dartboards. A Raspberry Pi handles the connection between the physical dartboard and the Dan's Playground platform.

---

## 🚀 Installation on a new Raspberry Pi

### Prerequisites

- Debian / Raspberry Pi OS 64-bit
- Internet connection
- SSH access
- `sudo` privileges

### 1. Install Git

On a freshly installed system, first install Git:

```bash
sudo apt update
sudo apt install -y git
```

### 2. Download Dan's Playground

The repository is public and can be cloned directly via HTTPS:

```bash
sudo git clone https://github.com/DNLBRNR/dansplayground-client.git /root/dans-playground
```

### 3. Start the installation

```bash
sudo /root/dans-playground/install.sh
```

The installer will automatically take care of:

- required system packages
- Python environment for the Dart Bridge
- required Python packages
- Dan's Playground Board Agent
- local Board Manager
- Autodarts
- systemd services
- automatic GitHub updater
- update timer

The individual board identity is **not** stored in the GitHub repository.

---

## 🔄 Automatic Updates

After installation, Dan's Playground automatically checks for new versions in the GitHub repository at regular intervals.

Updates are performed exclusively through:

```text
GitHub → update.sh
```

The official Autodarts updater remains disabled.

---

## 🗑️ Uninstallation

If Dan's Playground should be completely removed from a Raspberry Pi:

```bash
sudo /root/dans-playground/uninstall.sh
```

The uninstaller asks for confirmation before proceeding.

The following will be removed, among other things:

- Dan's Playground services
- update timer
- `/root/dans-playground`
- `/var/lib/dans-playground`
- `/etc/dans-playground`

The GitHub repository itself will **not** be modified.

---

## 📁 Important Directories

| Path | Description |
|---|---|
| `/root/dans-playground` | Local installation |
| `/var/lib/dans-playground` | Persistent board data |
| `/etc/dans-playground` | System-wide configuration |
| `/var/lib/dans-playground/board.json` | Individual board identity |

`board.json` is intentionally not stored in GitHub because this file contains the identity of the individual board.

---

## 🧪 Testing a New Installation

For a new test Pi, the following is sufficient:

```bash
sudo apt update
sudo apt install -y git
sudo git clone https://github.com/DNLBRNR/dansplayground-client.git /root/dans-playground
sudo /root/dans-playground/install.sh
```

This allows a complete installation to be reproduced and tested.

---

## 📌 Project Status

Dan's Playground is currently under active development.

The current installation includes, among other things:

- Autodarts Board Software
- Dan's Playground Board Agent
- local Board Manager
- Dart Bridge
- automatic GitHub updates
- board provisioning / pairing

Further features such as user accounts, multiple boards, and online multiplayer are part of the ongoing development.
