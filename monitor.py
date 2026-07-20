"""Measures per-WAN link quality (latency / jitter / loss) via ping."""

import re
import subprocess
from datetime import datetime

from config import CHECK_TARGETS, LOG_FILE, WAN_CONFIG


def run_ping(interface, target, count=2):
    cmd = ["ping", "-I", interface, "-c", str(count), "-W", "1", target]
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def parse_ping(output):
    rtts = [float(m) for m in re.findall(r"time=([\d.]+)", output)]

    latency = sum(rtts) / len(rtts) if rtts else None

    jitter = 0
    if len(rtts) > 1:
        diffs = [abs(rtts[i] - rtts[i - 1]) for i in range(1, len(rtts))]
        jitter = sum(diffs) / len(diffs)

    loss_match = re.search(r"(\d+)% packet loss", output)
    loss = float(loss_match.group(1)) if loss_match else 100

    return latency, jitter, loss


def is_up(interface):
    try:
        with open(f"/sys/class/net/{interface}/operstate") as f:
            return f.read().strip() == "up"
    except OSError:
        return False


def test_wan(name):
    iface = WAN_CONFIG[name]["iface"]
    gw = WAN_CONFIG[name]["gw"]

    result = {"up": is_up(iface), "lat": 999, "jit": 999, "loss": 100}

    if not result["up"]:
        return result

    # Step 1: gateway reachability.
    _, _, gw_loss = parse_ping(run_ping(iface, gw))
    if gw_loss == 100:
        return result  # WAN effectively down

    # Step 2: multi-target internet quality.
    lats, jits, losses = [], [], []
    for target in CHECK_TARGETS:
        lat, jit, loss = parse_ping(run_ping(iface, target))
        if lat is not None:
            lats.append(lat)
            jits.append(jit)
            losses.append(loss)

    if lats:
        result["lat"] = sum(lats) / len(lats)
        result["jit"] = sum(jits) / len(jits)
        result["loss"] = sum(losses) / len(losses)

    return result


def log_status(metrics, active):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    parts = [now]
    for name, w in metrics.items():
        parts.append(
            f"{name} {'up' if w['up'] else 'down'} "
            f"lat={w['lat']:.1f} jit={w['jit']:.1f} loss={w['loss']:.1f}"
        )
    parts.append(f"ACTIVE={active}")
    line = " | ".join(parts) + "\n"
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line)
    except OSError:
        pass  # logging must never crash the controller


def get_wan_metrics(active="UNKNOWN"):
    metrics = {name: test_wan(name) for name in WAN_CONFIG}
    log_status(metrics, active)
    return metrics
