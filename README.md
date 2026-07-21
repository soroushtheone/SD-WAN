# SD-WAN Controller

A lightweight dual-WAN (multi-WAN) failover and quality-based routing
controller for Linux. It configures each WAN interface, then continuously
measures latency, jitter, and packet loss and keeps the **default route** on
the best healthy link — fully automatically.

## Control panel: one file to run, one file to configure

- **`config.py`** – the only file you edit. Define your WANs (interface,
  gateway, static IP or DHCP), thresholds, and timings here.
- **`main.py`** – your control panel. Run it and it does everything:
  configures the interfaces, applies the default route, monitors the links,
  and fails over on its own.

> You never run `ip addr`, `dhclient`, or `ip route` by hand, and there are
> **no iptables rules** — the controller manages addressing and a single
> default route automatically.

## Project structure

```
config.py          # all settings (WANs, addressing, gateways, targets, SLA, timings)
main.py            # control panel / entry point (the orchestrator loop)
interface.py       # discovers NICs and applies static IP / DHCP from config
monitor.py         # measures latency / jitter / loss per WAN via ping
policy_engine.py   # picks the best WAN using SLA + weighted score
router.py          # applies / switches the default route automatically
sdwan.service      # systemd unit to run on boot
```

## Requirements

- Linux with `ip` (iproute2), `ping`, and `dhclient` (for DHCP WANs)
- Python 3.8+
- Root privileges (configuring interfaces and routes requires it)

## Configure

Edit `config.py`. Each WAN supports static or DHCP addressing:

```python
WAN_CONFIG = {
    "WAN1": {"iface": "enp10s0", "gw": "192.168.4.254",
             "dhcp": False, "ip": "192.168.4.10", "prefix": 24},  # static
    "WAN2": {"iface": "enp11s0", "gw": "192.168.201.1",
             "dhcp": True},                                       # DHCP
}
PRIMARY_WAN = "WAN1"
```

Add more WANs, tune the SLA thresholds, scoring weights, and switch timings —
the controller adapts automatically.

## Run manually

```bash
sudo python3 main.py
```

## Run on boot (systemd)

1. Copy the project to the device (path must match the unit file, default
   `/opt/sdwan`):

   ```bash
   sudo mkdir -p /opt/sdwan
   sudo cp -r ./* /opt/sdwan/
   ```

2. Install and enable the service:

   ```bash
   sudo cp /opt/sdwan/sdwan.service /etc/systemd/system/sdwan.service
   sudo systemctl daemon-reload
   sudo systemctl enable --now sdwan
   ```

3. Check status / logs:

   ```bash
   systemctl status sdwan
   journalctl -u sdwan -f
   ```

> If you install to a different directory, update `WorkingDirectory` and
> `ExecStart` in `sdwan.service` accordingly.

## How it works

1. On startup the controller discovers NICs and applies each WAN's addressing
   (static IP or DHCP) from `config.py`.
2. It applies the default route to `PRIMARY_WAN`.
3. Every `POLL_INTERVAL` seconds it pings the gateway and internet targets on
   every WAN and computes a quality score (lower = better).
4. A WAN breaching any SLA threshold is marked **bad**.
5. If the **active** link breaks SLA, it fails over immediately to the best
   available link.
6. Otherwise it only switches after `HOLD_TIME` and when another link is
   clearly better (score < active * `SWITCH_MARGIN`), preventing flapping.

## Status

- Interface addressing (static / DHCP): working.
- Dual-WAN failover and quality-based switching: working.
