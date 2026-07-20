# SD-WAN Controller

A lightweight dual-WAN (multi-WAN) failover and quality-based routing
controller for Linux. It continuously measures each WAN link's latency,
jitter, and packet loss, then keeps the **default route** on the best
healthy link — fully automatically.

## Control panel: one file to run, one file to configure

- **`config.py`** – the only file you edit. Define your WANs, thresholds,
  and timings here.
- **`main.py`** – your control panel. Run it and it does everything:
  applies the default route on startup, monitors the links, and fails over
  on its own.

> You never add routes by hand. There are **no iptables rules** — the
> controller manages a single default route automatically.

## Project structure

```
config.py          # all settings (WANs, gateways, targets, SLA, timings)
main.py            # control panel / entry point (the orchestrator loop)
monitor.py         # measures latency / jitter / loss per WAN via ping
policy_engine.py   # picks the best WAN using SLA + weighted score
router.py          # applies / switches the default route automatically
```

## Requirements

- Linux with the `ip` (iproute2) and `ping` commands available
- Python 3.8+
- Root privileges (changing the default route requires it)

## Configure

Edit `config.py`. Example:

```python
WAN_CONFIG = {
    "WAN1": {"iface": "enp10s0", "gw": "192.168.4.254"},
    "WAN2": {"iface": "enp11s0", "gw": "192.168.201.1"},
}
PRIMARY_WAN = "WAN1"
```

You can add more WANs, tune the SLA thresholds, scoring weights, and the
switch timings — the controller adapts automatically.

## Run

```bash
sudo python3 main.py
```

## How it works

1. On startup the controller applies the default route to `PRIMARY_WAN`.
2. Every `POLL_INTERVAL` seconds it pings the gateway and internet targets
   on every WAN and computes a quality score (lower = better).
3. A WAN breaching any SLA threshold is marked **bad**.
4. If the **active** link breaks SLA, it fails over immediately to the best
   available link.
5. Otherwise it only switches after `HOLD_TIME` and when another link is
   clearly better (score < active * `SWITCH_MARGIN`), preventing flapping.

## Status

- Dual-WAN failover and quality-based switching: working.
