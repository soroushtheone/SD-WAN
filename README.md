# SD-WAN Controller

A lightweight Linux SD-WAN controller for multi-WAN failover, priority-based
link selection, and source-subnet routing policies.

The project is designed around one simple idea:

> Run one setup wizard, then control the device from one file: `config.py`.

## What It Does

- Detects physical network interfaces.
- Lets you choose one management-only port.
- Configures LAN-side interfaces for client networks.
- Creates VLAN interfaces on LAN ports.
- Configures the remaining ports as WAN links with static IP or DHCP.
- Assigns WAN priority, for example WAN1 first, WAN2 second, WAN3 third.
- Sends internet traffic through the highest-priority healthy link.
- Fails over when the active link fails SLA.
- Fails back when the primary link becomes healthy again.
- Adds source-subnet policies, for example:
  - `192.168.10.0/24` through `WAN2`
  - `192.168.20.0/24` through `WAN1`
- Supports a default policy:
  - `allow`: unmatched traffic uses the active WAN.
  - `deny`: only explicit subnet policies are routed.
- Checks required files, commands, Python syntax, service status, and common
  service path problems.

## Project Structure

```text
setup_wizard.py    # interactive setup and health check
config.py          # single control file for all device behavior
main.py            # controller loop
interface.py       # interface discovery and IP/DHCP setup
monitor.py         # latency, jitter, and packet-loss checks
policy_engine.py   # priority and SLA decision logic
router.py          # default route and source-policy routing
sdwan.service      # systemd service
install.sh         # installer for /opt/sdwan
requirements.txt   # Python package requirements
OS_REQUIREMENTS.md # Linux package requirements
```

## Requirements

- Linux
- Python 3.8+
- Root privileges
- `ip` from iproute2
- `ping`
- `dhclient` if a WAN uses DHCP
- `systemd` if you want the controller to run as a service

No third-party Python packages are required. `requirements.txt` is included for
clarity and says the project uses only the Python standard library.

Before installing, install the Linux system packages.

Debian / Ubuntu:

```bash
sudo apt update
sudo apt install -y python3 iproute2 iputils-ping isc-dhcp-client systemd
```

RHEL / CentOS / Fedora:

```bash
sudo dnf install -y python3 iproute iputils dhcp-client systemd
```

More detail is in `OS_REQUIREMENTS.md`.

## Step 1: Run the Setup Wizard

Run this on the SD-WAN device:

```bash
sudo python3 setup_wizard.py
```

The wizard will:

1. List physical interfaces and show existing IPv4 addresses.
2. Ask which interface is management-only.
3. Let you configure LAN-side interfaces.
4. Let you create VLAN interfaces on LAN ports.
5. Let you configure WAN interfaces with IP address and gateway.
6. Let you configure another interface or continue.
7. Ask for WAN priority order.
8. Ask for subnet routing policies.
9. Ask for default policy: `allow` or `deny`.
10. Write the final configuration to `config.py`.
11. Run a health check and show logs if something is wrong.

## Step 2: Review the Single Control File

All behavior is stored in `config.py`.

Example:

```python
MANAGEMENT_INTERFACE = "enp9s0"

LAN_CONFIG = {
    "LAN1": {"iface": "enp13s0", "ip": "192.168.10.1", "prefix": 24},
}

VLAN_CONFIG = {
    "VLAN20": {
        "parent": "enp13s0",
        "vlan_id": 20,
        "ip": "192.168.20.1",
        "prefix": 24,
    },
}

WAN_CONFIG = {
    "WAN1": {
        "iface": "enp10s0",
        "gw": "192.168.4.254",
        "dhcp": False,
        "ip": "192.168.4.10",
        "prefix": 24,
    },
    "WAN2": {
        "iface": "enp11s0",
        "gw": "192.168.201.1",
        "dhcp": True,
    },
}

WAN_PRIORITY = ["WAN1", "WAN2"]
PRIMARY_WAN = "WAN1"

SUBNET_POLICIES = [
    {"source": "192.168.10.0/24", "wan": "WAN2"},
    {"source": "192.168.20.0/24", "wan": "WAN1"},
]

DEFAULT_POLICY = "allow"
```

## Step 3: Run the Controller Manually

```bash
sudo python3 main.py
```

The controller will:

1. Bring up configured LAN, VLAN, and WAN interfaces.
2. Apply static IP or DHCP settings.
3. Start with the primary WAN.
4. Monitor latency, jitter, and packet loss.
5. Switch to backup WANs if the active WAN fails.
6. Switch back to the primary WAN when it recovers.
7. Apply source-subnet routing policies.

## Step 4: Install as a Service

```bash
sudo ./install.sh
```

The installer copies the project to `/opt/sdwan`, installs `sdwan.service`,
and starts the controller.

If you want to run the service from the current project directory instead of
copying to `/opt/sdwan`, run:

```bash
sudo INSTALL_DIR="$(pwd)" ./install.sh
```

Useful commands:

```bash
systemctl status sdwan
journalctl -u sdwan -f
sudo systemctl restart sdwan
```

## How Priority Failover Works

`WAN_PRIORITY` controls link preference.

```python
WAN_PRIORITY = ["WAN1", "WAN2", "WAN3"]
```

The controller always chooses the first healthy WAN in that list.

If `WAN1` fails, traffic moves to `WAN2`.
If `WAN1` becomes healthy again, traffic moves back to `WAN1`.

## How Subnet Policies Work

`SUBNET_POLICIES` controls source-based routing.

```python
SUBNET_POLICIES = [
    {"source": "192.168.10.0/24", "wan": "WAN2"},
    {"source": "192.168.20.0/24", "wan": "WAN1"},
]
```

The router creates Linux policy-routing rules with `ip rule` and per-WAN
routing tables.

## Health Check

The wizard checks:

- Required project files.
- Required Linux commands.
- Python syntax.
- `sdwan` service status, if systemd is available.
- Recent service logs if the service is not active.
- A wrong systemd `WorkingDirectory` path, which causes `status=200/CHDIR`.

## Presentation Summary

This project is a small SD-WAN controller that turns a Linux device into a
multi-WAN router. It separates management traffic from WAN traffic, configures
LAN, VLAN, and WAN interfaces automatically, monitors link quality, performs
priority failover and failback, and supports policy routing for different
source subnets.
