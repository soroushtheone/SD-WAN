#!/usr/bin/env bash
#
# SD-WAN Controller installer.
# Copies the project to /opt/sdwan, installs the systemd service, and
# enables it to run on boot. Run as root:
#
#     sudo ./install.sh
#
# A reinstall never overwrites an existing /opt/sdwan/config.py, so your
# device settings are preserved. Delete it first to reset to defaults.
#
set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/sdwan}"
SERVICE_NAME="sdwan"
SERVICE_FILE="${SERVICE_NAME}.service"
SYSTEMD_PATH="/etc/systemd/system/${SERVICE_FILE}"

# Directory this script lives in (the project source).
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- Require root ---
if [[ "${EUID}" -ne 0 ]]; then
    echo "[install] Please run as root:  sudo ./install.sh" >&2
    exit 1
fi

# --- Basic dependency checks ---
command -v python3 >/dev/null 2>&1 || { echo "[install] python3 not found" >&2; exit 1; }
command -v systemctl >/dev/null 2>&1 || { echo "[install] systemctl not found" >&2; exit 1; }

echo "[install] Installing SD-WAN controller to ${INSTALL_DIR}"
mkdir -p "${INSTALL_DIR}"

# --- Copy code modules (always refreshed) ---
for f in interface.py monitor.py policy_engine.py router.py main.py setup_wizard.py requirements.txt OS_REQUIREMENTS.md README.md; do
    if [[ "${SRC_DIR}/${f}" != "${INSTALL_DIR}/${f}" ]]; then
        cp -f "${SRC_DIR}/${f}" "${INSTALL_DIR}/"
    fi
done

# --- Copy config only if it does not already exist (preserve device settings) ---
if [[ -f "${INSTALL_DIR}/config.py" ]]; then
    echo "[install] Existing config.py found -> keeping your settings"
else
    if [[ "${SRC_DIR}/config.py" != "${INSTALL_DIR}/config.py" ]]; then
        cp -f "${SRC_DIR}/config.py" "${INSTALL_DIR}/"
    fi
    echo "[install] Installed default config.py (edit it for your device)"
fi

# --- Install the systemd unit with the actual install path ---
echo "[install] Installing systemd service: ${SYSTEMD_PATH}"
cat > "${SYSTEMD_PATH}" <<EOF
[Unit]
Description=SD-WAN Controller (multi-WAN failover + policy routing)
Documentation=https://github.com/soroushtheone/SD-WAN
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=${INSTALL_DIR}
ExecStart=/usr/bin/python3 ${INSTALL_DIR}/main.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# --- Enable + (re)start ---
echo "[install] Reloading systemd and enabling the service"
systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"
systemctl restart "${SERVICE_NAME}"

echo
echo "[install] Done. SD-WAN controller is installed and running."
echo "  Status : systemctl status ${SERVICE_NAME}"
echo "  Logs   : journalctl -u ${SERVICE_NAME} -f"
echo "  Config : ${INSTALL_DIR}/config.py  (edit, then: systemctl restart ${SERVICE_NAME})"
