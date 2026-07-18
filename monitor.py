import subprocess
import re
from datetime import datetime

LOG_FILE = "/var/log/sdwan.log"

WAN_CONFIG = {
    "WAN1": {"iface": "enp10s0", "gw": "192.168.4.254"},
    "WAN2": {"iface": "enp11s0", "gw": "192.168.201.1"},
}

TARGETS = ["217.218.127.127", "5.200.200.200", "1.1.1.1"]


def run_ping(interface, target):
    cmd = ["ping", "-I", interface, "-c", "2", "-W", "1", target]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout


def parse_ping(output):
    rtts = []

    for line in output.split("\n"):
        m = re.search(r"time=([\d.]+)", line)
        if m:
            rtts.append(float(m.group(1)))

    latency = sum(rtts) / len(rtts) if rtts else None

    jitter = 0
    if rtts and len(rtts) > 1:
        diffs = [abs(rtts[i] - rtts[i - 1]) for i in range(1, len(rtts))]
        jitter = sum(diffs) / len(diffs)

    loss_match = re.search(r"(\d+)% packet loss", output)
    loss = float(loss_match.group(1)) if loss_match else 100

    return latency, jitter, loss


def is_up(interface):
    try:
        with open(f"/sys/class/net/{interface}/operstate") as f:
            return f.read().strip() == "up"
    except:
        return False


def test_wan(name):
    iface = WAN_CONFIG[name]["iface"]
    gw = WAN_CONFIG[name]["gw"]

    result = {
        "up": is_up(iface),
        "lat": 999,
        "jit": 999,
        "loss": 100
    }

    if not result["up"]:
        return result

    # ---- Step 1: Gateway test ----
    gw_ping = run_ping(iface, gw)
    gw_lat, _, gw_loss = parse_ping(gw_ping)

    if gw_loss == 100:
        return result  # WAN effectively down

    # ---- Step 2: Multi-target internet test ----
    latencies = []
    jitters = []
    losses = []

    for target in TARGETS:
        out = run_ping(iface, target)
        lat, jit, loss = parse_ping(out)

        if lat is not None:
            latencies.append(lat)
            jitters.append(jit)
            losses.append(loss)

    if latencies:
        result["lat"] = sum(latencies) / len(latencies)
        result["jit"] = sum(jitters) / len(jitters)
        result["loss"] = sum(losses) / len(losses)
    else:
        result["loss"] = 100

    return result


def log_status(w1, w2, active):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    line = (
        f"{now} | "
        f"WAN1 {'up' if w1['up'] else 'down'} lat={w1['lat']:.1f} jit={w1['jit']:.1f} loss={w1['loss']:.1f} | "
        f"WAN2 {'up' if w2['up'] else 'down'} lat={w2['lat']:.1f} jit={w2['jit']:.1f} loss={w2['loss']:.1f} | "
        f"ACTIVE={active}\n"
    )

    with open(LOG_FILE, "a") as f:
        f.write(line)


def get_wan_metrics(active="UNKNOWN"):
    wan1 = test_wan("WAN1")
    wan2 = test_wan("WAN2")

    log_status(wan1, wan2, active)

    return {
        "WAN1": wan1,
        "WAN2": wan2
    }
