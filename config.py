"""Central configuration for the SD-WAN controller.

This is the only file you edit on the device to control the whole system.
Use setup_wizard.py to generate it interactively, or edit it by hand.
main.py reads these values and applies management-port exclusion, interface
addressing, priority failover, and source-subnet policies automatically.
"""

# Management-only interface. This port is never selected as a WAN link and is
# left available for SSH/web/admin access.
MANAGEMENT_INTERFACE = "enp9s0"

# LAN interfaces. These are inside/client-side networks, not WAN uplinks.
LAN_CONFIG = {
    "LAN1": {"iface": "enp13s0", "ip": "192.168.10.1", "prefix": 24},
}

# VLAN interfaces created on LAN ports. The interface name becomes
# "<parent>.<vlan_id>", for example enp13s0.20.
VLAN_CONFIG = {
    "VLAN20": {
        "parent": "enp13s0",
        "vlan_id": 20,
        "ip": "192.168.20.1",
        "prefix": 24,
    },
}

# --- WAN interface + addressing definitions ---
# Add or remove WANs here; the controller adapts automatically.
#
# Per-WAN fields:
#   iface  : NIC name on the device (required)
#   gw     : default gateway for this WAN (required)
#   dhcp   : True  -> obtain IP automatically via DHCP
#            False -> apply the static "ip"/"prefix" below
#   ip     : static IPv4 address         (only when dhcp is False)
#   prefix : static prefix length (CIDR) (only when dhcp is False)
#
# main.py brings every interface up and applies this addressing on
# startup, so you never run `ip addr` / `dhclient` by hand.
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

# WAN priority order. The controller always uses the first healthy link.
# If WAN1 fails it moves to WAN2; when WAN1 becomes healthy again it fails back.
WAN_PRIORITY = ["WAN1", "WAN2"]

# WAN that should be active when the controller starts.
PRIMARY_WAN = "WAN1"

# Source-subnet routing policies.
# Each policy sends traffic from "source" through the selected WAN.
SUBNET_POLICIES = [
    {"source": "192.168.10.0/24", "wan": "WAN2"},
    {"source": "192.168.20.0/24", "wan": "WAN1"},
]

# What to do with traffic that does not match SUBNET_POLICIES.
# "allow" = use the active/default WAN.
# "deny"  = do not install a normal default route for unmatched traffic.
DEFAULT_POLICY = "allow"

# Linux policy-routing table IDs start here. Each WAN gets one table.
ROUTING_TABLE_BASE = 100

# --- Ping targets used to measure internet quality ---
CHECK_TARGETS = ["217.218.127.127", "5.200.200.200", "1.1.1.1"]

# --- SLA thresholds (a WAN breaching any of these is considered "bad") ---
SLA = {
    "max_latency": 120,   # ms
    "max_jitter": 20,     # ms
    "max_loss": 5,        # %
}

# --- Metric scoring weights (lower total score = better link) ---
SCORE_WEIGHTS = {"latency": 0.5, "jitter": 0.3, "loss": 0.2}

# --- Control loop / stability settings ---
HOLD_TIME = 30       # minimum seconds between default-route switches
POLL_INTERVAL = 3    # seconds between control-loop iterations
SWITCH_MARGIN = 0.8  # switch only if candidate score < active score * margin

# --- DHCP client command (used when a WAN has dhcp: True) ---
# {iface} is replaced with the interface name.
DHCP_COMMAND = ["dhclient", "-1", "{iface}"]

# --- Logging ---
LOG_FILE = "/var/log/sdwan.log"
