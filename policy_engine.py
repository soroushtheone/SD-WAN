class PolicyEngine:

    # --- SLA thresholds (tunable) ---
    MAX_LATENCY = 120      # ms
    MAX_JITTER = 20        # ms
    MAX_LOSS = 5           # %

    def wan_bad(self, wan):
        return (
            wan["lat"] > self.MAX_LATENCY or
            wan["jit"] > self.MAX_JITTER or
            wan["loss"] > self.MAX_LOSS
        )

    def decide(self, app, metrics, wan_state):

        wan1 = metrics["WAN1"]
        wan2 = metrics["WAN2"]

        wan1_up = wan_state["WAN1"]
        wan2_up = wan_state["WAN2"]

        # mark unusable WANs
        wan1_bad = not wan1_up or self.wan_bad(wan1)
        wan2_bad = not wan2_up or self.wan_bad(wan2)

        def score(w):
            return w["lat"] * 0.5 + w["jit"] * 0.3 + w["loss"] * 0.2

        # -------------------------
        # VOIP (strict SLA)
        # -------------------------
        if app == "voip":

            if not wan1_bad and not wan2_bad:
                return "WAN1" if score(wan1) < score(wan2) else "WAN2"

            if not wan1_bad:
                return "WAN1"

            if not wan2_bad:
                return "WAN2"

            return None

        # -------------------------
        # VIDEO (moderate SLA)
        # -------------------------
        if app == "video":

            if not wan1_bad and not wan2_bad:
                return "WAN1" if score(wan1) < score(wan2) else "WAN2"

            if not wan1_bad:
                return "WAN1"

            return "WAN2"

        # -------------------------
        # BULK (loose SLA)
        # -------------------------
        if not wan1_bad and not wan2_bad:
            return "WAN1" if score(wan1) < score(wan2) else "WAN2"

        if not wan1_bad:
            return "WAN1"

        return "WAN2"
