import time
from monitor import get_wan_metrics
from policy_engine import PolicyEngine
from router import Router
from marker import Marker

engine = PolicyEngine()
router = Router()
marker = Marker()

CURRENT_WAN = "WAN1"
VOIP_WAN = "WAN1"

while True:

    metrics = get_wan_metrics(CURRENT_WAN)

    wan_state = {
        "WAN1": metrics["WAN1"]["up"],
        "WAN2": metrics["WAN2"]["up"]
    }

    # -------------------------
    # GLOBAL DEFAULT WAN (fallback traffic)
    # -------------------------
    best_wan = engine.decide("bulk", metrics, wan_state)

    if best_wan and best_wan != CURRENT_WAN:
        print(f"[SD-WAN] Switching default {CURRENT_WAN} → {best_wan}")
        if router.switch(best_wan):
            CURRENT_WAN = best_wan

    # -------------------------
    # VOIP DECISION (independent)
    # -------------------------
    voip_wan = engine.decide("voip", metrics, wan_state)

    if voip_wan and voip_wan != VOIP_WAN:
        marker.set_voip_wan(voip_wan)
        VOIP_WAN = voip_wan

    time.sleep(3)
