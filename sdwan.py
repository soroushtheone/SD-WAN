import subprocess
import time
import re
from collections import deque

WAN1_IF = "enp10s0"
WAN2_IF = "enp11s0"

WAN1_GW = "192.168.4.254"
WAN2_GW = "192.168.201.1"

CHECK_TARGET = "8.8.8.8"

HOLD_TIME = 30
WINDOW_SIZE = 5

CURRENT = "WAN1"
LAST_SWITCH = time.time()

wan1_hist = deque(maxlen=WINDOW_SIZE)
wan2_hist = deque(maxlen=WINDOW_SIZE)


def is_interface_up(interface):
    try:
        with open(f"/sys/class/net/{interface}/operstate") as f:
            return "up" in f.read()
    except:
        return False


def ping_gateway(interface, gw):
    cmd = ["ping", "-I", interface, "-c", "2", "-W", "1", gw]
    return subprocess.run(cmd).returncode == 0


def ping_raw(interface):
    cmd = ["ping", "-I", interface, "-c", "5", "-W", "1", CHECK_TARGET]
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def parse_ping(output):
    rtts = []

    for line in output.split("\n"):
        m = re.search(r"time=([\d.]+)", line)
        if m:
            rtts.append(float(m.group(1)))

    latency = sum(rtts) / len(rtts) if rtts else 999

    jitter = 0
    if len(rtts) > 1:
        diffs = [abs(rtts[i] - rtts[i-1]) for i in range(1, len(rtts))]
        jitter = sum(diffs) / len(diffs)

    loss_match = re.search(r"(\d+)% packet loss", output)
    loss = float(loss_match.group(1)) if loss_match else 100

    return latency, jitter, loss


def avg(hist):
    if not hist:
        return (999, 999, 100)
    return (
        sum(x[0] for x in hist) / len(hist),
        sum(x[1] for x in hist) / len(hist),
        sum(x[2] for x in hist) / len(hist),
    )


def score(lat, jit, loss):
    return lat * 0.5 + jit * 0.3 + loss * 0.2


def switch_default(wan):
    global CURRENT, LAST_SWITCH

    if wan == "WAN1":
        subprocess.run(["ip", "route", "replace", "default", "via", WAN1_GW, "dev", WAN1_IF])
    else:
        subprocess.run(["ip", "route", "replace", "default", "via", WAN2_GW, "dev", WAN2_IF])

    print(f"[SWITCH BULK] → {wan}")
    CURRENT = wan
    LAST_SWITCH = time.time()


while True:
    now = time.time()

    # HARD FAIL
    if not is_interface_up(WAN1_IF) or not ping_gateway(WAN1_IF, WAN1_GW):
        if CURRENT != "WAN2":
            switch_default("WAN2")
        time.sleep(3)
        continue

    if not is_interface_up(WAN2_IF) or not ping_gateway(WAN2_IF, WAN2_GW):
        if CURRENT != "WAN1":
            switch_default("WAN1")
        time.sleep(3)
        continue

    # METRICS
    wan1_hist.append(parse_ping(ping_raw(WAN1_IF)))
    wan2_hist.append(parse_ping(ping_raw(WAN2_IF)))

    w1 = avg(wan1_hist)
    w2 = avg(wan2_hist)

    s1 = score(*w1)
    s2 = score(*w2)

    print(f"WAN1 score={s1:.2f} | WAN2 score={s2:.2f} | ACTIVE={CURRENT}")

    if now - LAST_SWITCH > HOLD_TIME:
        if CURRENT == "WAN1" and s2 < s1 * 0.8:
            switch_default("WAN2")

        elif CURRENT == "WAN2" and s1 < s2 * 0.8:
            switch_default("WAN1")

    time.sleep(5)
