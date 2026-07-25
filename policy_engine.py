"""Decides which WAN should carry traffic based on priority + SLA."""

import config

SCORE_WEIGHTS = getattr(config, "SCORE_WEIGHTS", {"latency": 0.5, "jitter": 0.3, "loss": 0.2})
SLA = getattr(config, "SLA", {"max_latency": 120, "max_jitter": 20, "max_loss": 5})
WAN_PRIORITY = getattr(config, "WAN_PRIORITY", list(getattr(config, "WAN_CONFIG", {})))


class PolicyEngine:

    def wan_bad(self, wan):
        return (
            not wan["up"]
            or wan["lat"] > SLA["max_latency"]
            or wan["jit"] > SLA["max_jitter"]
            or wan["loss"] > SLA["max_loss"]
        )

    def score(self, wan):
        return (
            wan["lat"] * SCORE_WEIGHTS["latency"]
            + wan["jit"] * SCORE_WEIGHTS["jitter"]
            + wan["loss"] * SCORE_WEIGHTS["loss"]
        )

    def priority_order(self, names):
        configured = [name for name in WAN_PRIORITY if name in names]
        extras = sorted(name for name in names if name not in configured)
        return configured + extras

    def decide(self, metrics):
        """Return the best WAN name.

        Uses the first healthy WAN in WAN_PRIORITY order. This gives predictable
        primary/backup behavior and automatic failback when a higher-priority
        link recovers. If no link meets SLA, it falls back to the first link
        that is still physically up.
        """
        for name in self.priority_order(metrics):
            if not self.wan_bad(metrics[name]):
                return name

        for name in self.priority_order(metrics):
            if metrics[name]["up"]:
                return name

        return None
