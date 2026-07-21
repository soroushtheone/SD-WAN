"""SD-WAN control panel.

The single entry point. It reads everything from config.py and manages the
interfaces and default route automatically — you never run `ip addr`,
`dhclient`, or `ip route` by hand. Just edit config.py, then run:

    sudo python3 main.py
"""

import time

from config import HOLD_TIME, POLL_INTERVAL, PRIMARY_WAN, SWITCH_MARGIN
from interface import setup_all
from monitor import get_wan_metrics
from policy_engine import PolicyEngine
from router import Router


def main():
    engine = PolicyEngine()
    router = Router()

    # Discover NICs and apply addressing (static / DHCP) from config.py.
    print("[SD-WAN] Configuring interfaces...")
    setup_all()

    active = PRIMARY_WAN
    print(f"[SD-WAN] Applying primary WAN: {active}")

    # Apply the initial route automatically on startup.
    if not router.apply(active):
        print(f"[SD-WAN] Primary {active} unavailable; will pick a link from metrics.")
        active = None

    last_switch = 0

    while True:
        metrics = get_wan_metrics(active or "NONE")
        best = engine.decide(metrics)

        if best is None:
            print("[SD-WAN] All WANs are down!")
            time.sleep(POLL_INTERVAL)
            continue

        # No active link yet -> take the best one immediately.
        if active is None:
            if router.apply(best):
                active = best
                last_switch = time.time()
            time.sleep(POLL_INTERVAL)
            continue

        status = " | ".join(
            f"{n} score={engine.score(w):.2f}" for n, w in metrics.items()
        )
        print(f"{status} | ACTIVE={active}")

        now = time.time()

        # Immediate failover if the active link breaches SLA.
        if engine.wan_bad(metrics[active]) and best != active:
            print(f"[SD-WAN] Active {active} failed SLA -> failover to {best}")
            if router.apply(best):
                active = best
                last_switch = now

        # Otherwise switch only after HOLD_TIME and a clear improvement.
        elif best != active and (now - last_switch) > HOLD_TIME:
            if engine.score(metrics[best]) < engine.score(metrics[active]) * SWITCH_MARGIN:
                print(f"[SD-WAN] {best} is clearly better -> switching from {active}")
                if router.apply(best):
                    active = best
                    last_switch = now

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
