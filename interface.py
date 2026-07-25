"""Interface discovery and automatic IP assignment.

Reads config.py and applies management, LAN, VLAN, and WAN interface settings.
"""

import os
import subprocess

import config

DHCP_COMMAND = getattr(config, "DHCP_COMMAND", ["dhclient", "-1", "{iface}"])
LAN_CONFIG = getattr(config, "LAN_CONFIG", {})
MANAGEMENT_INTERFACE = getattr(config, "MANAGEMENT_INTERFACE", "")
VLAN_CONFIG = getattr(config, "VLAN_CONFIG", {})
WAN_CONFIG = getattr(config, "WAN_CONFIG", {})

SYS_NET = "/sys/class/net"


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def list_interfaces():
    """Return the names of all real physical network interfaces."""
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


def apply_static(iface, ip, prefix, flush=True):
    if flush:
        subprocess.run(["ip", "addr", "flush", "dev", iface], check=False)
    result = run(["ip", "addr", "add", f"{ip}/{prefix}", "dev", iface])
    if result.returncode != 0 and "File exists" not in result.stderr:
        print(f"[IFACE] {iface} static IP failed: {result.stderr.strip()}")
        return False
    print(f"[IFACE] {iface} -> {ip}/{prefix} (static)")
    return True


def apply_dhcp(iface):
    cmd = [part.format(iface=iface) for part in DHCP_COMMAND]
    result = run(cmd)
    if result.returncode != 0:
        print(f"[IFACE] {iface} DHCP failed: {result.stderr.strip()}")
        return False
    print(f"[IFACE] {iface} -> DHCP")
    return True


def setup_static_interface(name, iface, ip, prefix):
    if not iface or not interface_exists(iface):
        print(f"[IFACE] {name}: interface '{iface}' not found on device")
        return False
    bring_up(iface)
    return apply_static(iface, ip, prefix)


def setup_lan(name, cfg):
    return setup_static_interface(name, cfg.get("iface"), cfg.get("ip"), cfg.get("prefix"))


def vlan_iface_name(parent, vlan_id):
    return f"{parent}.{vlan_id}"


def setup_vlan(name, cfg):
    parent = cfg.get("parent")
    vlan_id = cfg.get("vlan_id")
    ip = cfg.get("ip")
    prefix = cfg.get("prefix")

    if not parent or not interface_exists(parent):
        print(f"[VLAN] {name}: parent interface '{parent}' not found")
        return False
    if not vlan_id or not ip or not prefix:
        print(f"[VLAN] {name}: parent, vlan_id, ip, and prefix are required")
        return False

    iface = vlan_iface_name(parent, vlan_id)
    bring_up(parent)

    if not interface_exists(iface):
        result = run(["ip", "link", "add", "link", parent, "name", iface, "type", "vlan", "id", str(vlan_id)])
        if result.returncode != 0 and "File exists" not in result.stderr:
            print(f"[VLAN] {name}: create {iface} failed: {result.stderr.strip()}")
            return False

    bring_up(iface)
    return apply_static(iface, ip, prefix)


def setup_wan(name, cfg):
    iface = cfg.get("iface")

    if iface == MANAGEMENT_INTERFACE:
        print(f"[IFACE] {name}: refusing to use management interface '{iface}' as WAN")
        return False

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
    """Apply configured LAN, VLAN, and WAN addressing."""
    discovered = list_interfaces()
    print(f"[IFACE] Discovered interfaces: {', '.join(discovered) or 'none'}")
    print(f"[IFACE] Management interface: {MANAGEMENT_INTERFACE or 'not set'}")

    all_ok = True
    for name, cfg in LAN_CONFIG.items():
        if not setup_lan(name, cfg):
            all_ok = False
    for name, cfg in VLAN_CONFIG.items():
        if not setup_vlan(name, cfg):
            all_ok = False
    for name, cfg in WAN_CONFIG.items():
        if not setup_wan(name, cfg):
            all_ok = False
    return all_ok


if __name__ == "__main__":
    setup_all()
