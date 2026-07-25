#!/usr/bin/env python3
"""Interactive SD-WAN setup wizard.

Run this file as root on the SD-WAN device:

    sudo python3 setup_wizard.py

The wizard writes config.py. The running controller reads config.py, so this
keeps the device controlled by one simple file.
"""

import ast
import os
import pprint
import shutil
import subprocess
import sys
from ipaddress import ip_address, ip_network
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
CONFIG_FILE = PROJECT_DIR / "config.py"
REQUIRED_FILES = [
    "config.py",
    "interface.py",
    "monitor.py",
    "policy_engine.py",
    "router.py",
    "main.py",
    "sdwan.service",
]
PYTHON_FILES = [
    "config.py",
    "interface.py",
    "monitor.py",
    "policy_engine.py",
    "router.py",
    "main.py",
    "setup_wizard.py",
]


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def ask(prompt, default=None):
    suffix = f" [{default}]" if default not in (None, "") else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value if value else default


def ask_choice(prompt, choices):
    while True:
        value = ask(prompt)
        if str(value).isdigit():
            index = int(value) - 1
            if 0 <= index < len(choices):
                return choices[index]
        if value in choices:
            return value
        numbered = ", ".join(f"{idx + 1}={choice}" for idx, choice in enumerate(choices))
        print(f"Choose one of: {numbered}")


def ask_yes_no(prompt, default="y"):
    value = ask(prompt, default).lower()
    return value in ("y", "yes")


def list_physical_interfaces():
    base = Path("/sys/class/net")
    if not base.exists():
        return []

    interfaces = []
    for path in sorted(base.iterdir()):
        name = path.name
        if name == "lo":
            continue
        if (path / "device").exists():
            interfaces.append(name)
    return interfaces


def interface_ipv4(iface):
    result = run(["ip", "-4", "-o", "addr", "show", "dev", iface])
    if result.returncode != 0 or not result.stdout.strip():
        return "-"
    addresses = []
    for line in result.stdout.splitlines():
        parts = line.split()
        if "inet" in parts:
            addresses.append(parts[parts.index("inet") + 1])
    return ", ".join(addresses) if addresses else "-"


def show_interfaces(interfaces, management=None):
    print("\nInterfaces:")
    for idx, iface in enumerate(interfaces, 1):
        role = "management" if iface == management else "available"
        print(f"  {idx}. {iface:12} ip={interface_ipv4(iface):18} {role}")


def load_existing_settings():
    if not CONFIG_FILE.exists():
        return {}

    tree = ast.parse(CONFIG_FILE.read_text(encoding="utf-8"))
    settings = {}
    wanted = {
        "MANAGEMENT_INTERFACE",
        "LAN_CONFIG",
        "VLAN_CONFIG",
        "WAN_CONFIG",
        "WAN_PRIORITY",
        "PRIMARY_WAN",
        "SUBNET_POLICIES",
        "DEFAULT_POLICY",
        "CHECK_TARGETS",
        "SLA",
        "SCORE_WEIGHTS",
        "HOLD_TIME",
        "POLL_INTERVAL",
        "SWITCH_MARGIN",
        "DHCP_COMMAND",
        "LOG_FILE",
        "ROUTING_TABLE_BASE",
    }
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in wanted:
                    try:
                        settings[target.id] = ast.literal_eval(node.value)
                    except ValueError:
                        pass
    return settings


def validate_ip(value):
    try:
        ip_address(value)
        return True
    except ValueError:
        return False


def validate_network(value):
    try:
        ip_network(value, strict=False)
        return True
    except ValueError:
        return False


def configure_wans(interfaces, management, reserved_interfaces=None):
    wan_config = {}
    reserved = set(reserved_interfaces or [])
    available = [iface for iface in interfaces if iface != management and iface not in reserved]
    if not available:
        print("No interfaces left for WAN after management/LAN selection.")
        return wan_config

    while True:
        show_interfaces(available, management)
        iface = ask_choice("Choose interface to configure as WAN", available)
        wan_name = ask("WAN name", f"WAN{len(wan_config) + 1}").upper()
        dhcp = ask_yes_no("Use DHCP for this WAN? y/n", "n")

        cfg = {"iface": iface, "dhcp": dhcp}
        if dhcp:
            gw = ask("Gateway for this WAN")
            while not validate_ip(gw):
                gw = ask("Gateway must be an IPv4 address")
            cfg["gw"] = gw
        else:
            ip_value = ask("Static IP address")
            while not validate_ip(ip_value):
                ip_value = ask("Static IP must be an IPv4 address")

            prefix = ask("Prefix length", "24")
            while not str(prefix).isdigit() or not (1 <= int(prefix) <= 32):
                prefix = ask("Prefix must be 1-32", "24")

            gw = ask("Gateway")
            while not validate_ip(gw):
                gw = ask("Gateway must be an IPv4 address")

            cfg.update({"ip": ip_value, "prefix": int(prefix), "gw": gw})

        wan_config[wan_name] = cfg
        print(f"\nSaved {wan_name}: {cfg}")
        available.remove(iface)

        if not available or not ask_yes_no("Configure another WAN interface? y/n", "y"):
            break

    return wan_config


def ask_static_address(label):
    ip_value = ask(f"{label} IP address")
    while not validate_ip(ip_value):
        ip_value = ask(f"{label} IP must be an IPv4 address")

    prefix = ask(f"{label} prefix length", "24")
    while not str(prefix).isdigit() or not (1 <= int(prefix) <= 32):
        prefix = ask(f"{label} prefix must be 1-32", "24")

    return ip_value, int(prefix)


def configure_lans(interfaces, management):
    lan_config = {}
    available = [iface for iface in interfaces if iface != management]

    print("\nLAN side configuration")
    while ask_yes_no("Configure a LAN interface? y/n", "y"):
        show_interfaces(available, management)
        iface = ask_choice("Choose LAN interface", available)
        lan_name = ask("LAN name", f"LAN{len(lan_config) + 1}").upper()
        ip_value, prefix = ask_static_address(lan_name)
        lan_config[lan_name] = {"iface": iface, "ip": ip_value, "prefix": prefix}
        print(f"\nSaved {lan_name}: {lan_config[lan_name]}")
        available.remove(iface)

        if not available or not ask_yes_no("Configure another LAN interface? y/n", "n"):
            break

    return lan_config


def configure_vlans(lan_config):
    vlan_config = {}
    if not lan_config:
        return vlan_config

    print("\nVLAN configuration")
    while ask_yes_no("Configure a VLAN interface on a LAN port? y/n", "n"):
        lan_names = list(lan_config)
        lan_name = ask_choice("Choose parent LAN", lan_names)
        parent = lan_config[lan_name]["iface"]

        vlan_id = ask("VLAN ID", "10")
        while not str(vlan_id).isdigit() or not (1 <= int(vlan_id) <= 4094):
            vlan_id = ask("VLAN ID must be 1-4094", "10")

        vlan_name = ask("VLAN name", f"VLAN{vlan_id}").upper()
        ip_value, prefix = ask_static_address(vlan_name)
        vlan_config[vlan_name] = {
            "parent": parent,
            "vlan_id": int(vlan_id),
            "ip": ip_value,
            "prefix": prefix,
        }
        print(f"\nSaved {vlan_name}: {vlan_config[vlan_name]}")

    return vlan_config


def configure_priority(wan_config):
    names = list(wan_config)
    priority = []
    print("\nSet link priority. Pick the primary first, then backups.")
    while len(priority) < len(names):
        remaining = [name for name in names if name not in priority]
        print(f"Remaining: {', '.join(remaining)}")
        choice = ask_choice("Next priority WAN", remaining)
        priority.append(choice)
    return priority


def configure_policies(wan_config):
    policies = []
    print("\nSubnet policies route a source subnet through a selected WAN.")
    while ask_yes_no("Add a subnet policy? y/n", "n"):
        source = ask("Source subnet, example 192.168.10.0/24")
        while not validate_network(source):
            source = ask("Enter a valid subnet, example 192.168.10.0/24")
        wan = ask_choice("Route this subnet through WAN", list(wan_config))
        policies.append({"source": str(ip_network(source, strict=False)), "wan": wan})

    default_policy = ask_choice("Default policy for unmatched traffic (allow/deny)", ["allow", "deny"])
    return policies, default_policy


def write_config(settings):
    config_text = f'''"""Central configuration for the SD-WAN controller.

This file is the single control point for the device. You can edit it by hand,
or run setup_wizard.py to regenerate it interactively.
"""

MANAGEMENT_INTERFACE = {settings["MANAGEMENT_INTERFACE"]!r}

LAN_CONFIG = {pprint.pformat(settings["LAN_CONFIG"], sort_dicts=False)}

VLAN_CONFIG = {pprint.pformat(settings["VLAN_CONFIG"], sort_dicts=False)}

WAN_CONFIG = {pprint.pformat(settings["WAN_CONFIG"], sort_dicts=False)}

WAN_PRIORITY = {pprint.pformat(settings["WAN_PRIORITY"], sort_dicts=False)}
PRIMARY_WAN = {settings["PRIMARY_WAN"]!r}

SUBNET_POLICIES = {pprint.pformat(settings["SUBNET_POLICIES"], sort_dicts=False)}
DEFAULT_POLICY = {settings["DEFAULT_POLICY"]!r}
ROUTING_TABLE_BASE = {settings["ROUTING_TABLE_BASE"]!r}

CHECK_TARGETS = {pprint.pformat(settings["CHECK_TARGETS"], sort_dicts=False)}

SLA = {pprint.pformat(settings["SLA"], sort_dicts=False)}
SCORE_WEIGHTS = {pprint.pformat(settings["SCORE_WEIGHTS"], sort_dicts=False)}

HOLD_TIME = {settings["HOLD_TIME"]!r}
POLL_INTERVAL = {settings["POLL_INTERVAL"]!r}
SWITCH_MARGIN = {settings["SWITCH_MARGIN"]!r}

DHCP_COMMAND = {pprint.pformat(settings["DHCP_COMMAND"], sort_dicts=False)}
LOG_FILE = {settings["LOG_FILE"]!r}
'''
    CONFIG_FILE.write_text(config_text, encoding="utf-8")
    print(f"\nWrote {CONFIG_FILE}")


def health_check():
    print("\nHealth check")
    ok = True

    for name in REQUIRED_FILES:
        path = PROJECT_DIR / name
        if path.exists():
            print(f"  OK   file exists: {name}")
        else:
            print(f"  FAIL missing file: {name}")
            ok = False

    for command in ("python3", "ip", "ping"):
        if shutil.which(command):
            print(f"  OK   command exists: {command}")
        else:
            print(f"  FAIL command missing: {command}")
            ok = False

    compile_result = run([sys.executable, "-m", "py_compile", *[str(PROJECT_DIR / name) for name in PYTHON_FILES]])
    if compile_result.returncode == 0:
        print("  OK   Python files compile")
    else:
        print("  FAIL Python compile error")
        print(compile_result.stderr.strip())
        ok = False

    if shutil.which("systemctl"):
        status = run(["systemctl", "is-active", "sdwan"])
        if status.stdout.strip() == "active":
            print("  OK   sdwan service is active")
        else:
            print("  WARN sdwan service is not active")
            logs = run(["journalctl", "-u", "sdwan", "-n", "30", "--no-pager"])
            if logs.stdout.strip():
                print("\nLast sdwan logs:")
                print(logs.stdout.strip())
                if "CHDIR" in logs.stdout or "Changing to the requested working directory failed" in logs.stdout:
                    print("\nService path problem detected.")
                    print("The installed sdwan.service points to a directory that does not exist.")
                    print("Fix it by reinstalling from this project directory:")
                    print(f"  cd {PROJECT_DIR}")
                    print(f"  sudo INSTALL_DIR={PROJECT_DIR} ./install.sh")
    else:
        print("  WARN systemctl not found; service check skipped")

    if ok:
        print("\nEverything needed by the app is present. You can run: sudo python3 main.py")
    else:
        print("\nFix the failed checks above, then run the wizard again.")
    return ok


def main():
    if os.name != "posix":
        print("This wizard must be run on the Linux SD-WAN device.")
        return

    existing = load_existing_settings()
    interfaces = list_physical_interfaces()
    if not interfaces:
        print("No physical interfaces found.")
        return

    show_interfaces(interfaces)
    management = ask_choice("Which port is management-only?", interfaces)
    lan_config = configure_lans(interfaces, management)
    vlan_config = configure_vlans(lan_config)
    lan_interfaces = [cfg["iface"] for cfg in lan_config.values()]
    wan_config = configure_wans(interfaces, management, lan_interfaces)
    if not wan_config:
        print("At least one WAN interface is required.")
        return
    priority = configure_priority(wan_config)
    policies, default_policy = configure_policies(wan_config)

    settings = {
        "MANAGEMENT_INTERFACE": management,
        "LAN_CONFIG": lan_config,
        "VLAN_CONFIG": vlan_config,
        "WAN_CONFIG": wan_config,
        "WAN_PRIORITY": priority,
        "PRIMARY_WAN": priority[0],
        "SUBNET_POLICIES": policies,
        "DEFAULT_POLICY": default_policy,
        "ROUTING_TABLE_BASE": existing.get("ROUTING_TABLE_BASE", 100),
        "CHECK_TARGETS": existing.get("CHECK_TARGETS", ["217.218.127.127", "5.200.200.200", "1.1.1.1"]),
        "SLA": existing.get("SLA", {"max_latency": 120, "max_jitter": 20, "max_loss": 5}),
        "SCORE_WEIGHTS": existing.get("SCORE_WEIGHTS", {"latency": 0.5, "jitter": 0.3, "loss": 0.2}),
        "HOLD_TIME": existing.get("HOLD_TIME", 30),
        "POLL_INTERVAL": existing.get("POLL_INTERVAL", 3),
        "SWITCH_MARGIN": existing.get("SWITCH_MARGIN", 0.8),
        "DHCP_COMMAND": existing.get("DHCP_COMMAND", ["dhclient", "-1", "{iface}"]),
        "LOG_FILE": existing.get("LOG_FILE", "/var/log/sdwan.log"),
    }

    print("\nFinal configuration preview:")
    print(pprint.pformat(settings, sort_dicts=False))

    if ask_yes_no("Write this configuration to config.py? y/n", "y"):
        write_config(settings)
        health_check()
    else:
        print("No changes written.")


if __name__ == "__main__":
    main()
