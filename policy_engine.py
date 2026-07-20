"""Decides which WAN should carry traffic based on SLA + quality score."""

from config import SCORE_WEIGHTS, SLA


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

    def decide(self, metrics):
        """Return the best WAN name.

        Prefers links that meet SLA; if none do, falls back to the
        least-bad link that is still up. Returns None if every WAN is down.
        """
        healthy = {n: w for n, w in metrics.items() if not self.wan_bad(w)}
        pool = healthy or {n: w for n, w in metrics.items() if w["up"]}

        if not pool:
            return None

        return min(pool, key=lambda n: self.score(pool[n]))
