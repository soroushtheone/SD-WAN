"""Automatic default-route management.

The operator never runs `ip route` manually — this module applies and
switches the default route based on the WAN chosen by the controller.
"""

import subprocess

from config import WAN_CONFIG


class Router:

    def is_link_up(self, iface):
        try:
            with open(f"/sys/class/net/{iface}/operstate") as f:
                return f.read().strip() == "up"
        except OSError:
            return False

    def show_routes(self):
        result = subprocess.run(["ip", "route"], capture_output=True, text=True)
        print("[ROUTES]\n", result.stdout)

    def apply(self, wan):
        """Force the default route onto the given WAN. Returns True on success."""
        if wan not in WAN_CONFIG:
            print(f"[ROUTER] invalid WAN: {wan}")
            return False

        iface = WAN_CONFIG[wan]["iface"]
        gw = WAN_CONFIG[wan]["gw"]

        if not self.is_link_up(iface):
            print(f"[ROUTER] {wan} interface {iface} is DOWN")
            return False

        # Clean any existing default route (safe even if none exists).
        subprocess.run(["ip", "route", "del", "default"], stderr=subprocess.DEVNULL)

        result = subprocess.run(
            ["ip", "route", "replace", "default", "via", gw, "dev", iface],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print("[ROUTER ERROR]", result.stderr.strip())
            return False

        print(f"[ROUTER] {wan} is now ACTIVE (via {gw} dev {iface})")
        return True
