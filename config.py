"""Central configuration for the SD-WAN controller.

This is the only file you edit on the device to control the whole system.
main.py reads these values and applies everything automatically (interface
addressing + default route + failover). You never run `ip`/`dhclient` by hand.
"""

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

# WAN that should be active when the controller starts.
PRIMARY_WAN = "WAN1"

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
