"""Interface discovery and automatic IP assignment.

Reads every physical NIC on the device and applies the addressing defined
in config.py (static IP or DHCP). All of this runs automatically from
main.py on startup — the operator never runs `ip addr` or `dhclient`.
"""

import os
import subprocess

from config import DHCP_COMMAND, WAN_CONFIG

SYS_NET = "/sys/class/net"


def list_interfaces():
    """Return the names of all real (physical) network interfaces.

    Skips loopback and virtual devices (veth, docker, bridges, etc.).
    A physical NIC has a `device` symlink under /sys/class/net/<name>.
    """
    interfaces = []
    try:
        names = sorted(os.listdir(SYS_NET))
    except OSError:
        return interfaces

    for name in names:
        if name == "lo":
            continue
        if os.path.exists(os.path.join(SYS_NET, name, "device")):
            interfaces.append(name)
    return interfaces


def interface_exists(iface):
    return os.path.exists(os.path.join(SYS_NET, iface))


def bring_up(iface):
    subprocess.run(["ip", "link", "set", iface, "up"], check=False)


def apply_static(iface, ip, prefix):
    # Clear any existing addresses so config.py is the single source of truth.
    subprocess.run(["ip", "addr", "flush", "dev", iface], check=False)
    result = subprocess.run(
        ["ip", "addr", "add", f"{ip}/{prefix}", "dev", iface],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"[IFACE] {iface} static IP failed: {result.stderr.strip()}")
        return False
    print(f"[IFACE] {iface} -> {ip}/{prefix} (static)")
    return True


def apply_dhcp(iface):
    cmd = [part.format(iface=iface) for part in DHCP_COMMAND]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[IFACE] {iface} DHCP failed: {result.stderr.strip()}")
        return False
    print(f"[IFACE] {iface} -> DHCP")
    return True


def setup_interface(name, cfg):
    """Bring one WAN's interface up and apply its addressing."""
    iface = cfg.get("iface")

    if not iface or not interface_exists(iface):
        print(f"[IFACE] {name}: interface '{iface}' not found on device")
        return False

    bring_up(iface)

    if cfg.get("dhcp"):
        return apply_dhcp(iface)

    ip = cfg.get("ip")
    prefix = cfg.get("prefix")
    if not ip or not prefix:
        print(f"[IFACE] {name}: dhcp is False but 'ip'/'prefix' missing")
        return False

    return apply_static(iface, ip, prefix)


def setup_all():
    """Discover NICs and apply addressing for every configured WAN.

    Returns True if every WAN was configured successfully.
    """
    discovered = list_interfaces()
    print(f"[IFACE] Discovered interfaces: {', '.join(discovered) or 'none'}")

    all_ok = True
    for name, cfg in WAN_CONFIG.items():
        if not setup_interface(name, cfg):
            all_ok = False
    return all_ok


if __name__ == "__main__":
    # Handy for a quick manual check: `sudo python3 interface.py`
    setup_all()
