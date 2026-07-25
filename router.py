"""Automatic default-route and source-policy routing management."""

import subprocess

import config

DEFAULT_POLICY = getattr(config, "DEFAULT_POLICY", "allow")
ROUTING_TABLE_BASE = getattr(config, "ROUTING_TABLE_BASE", 100)
SUBNET_POLICIES = getattr(config, "SUBNET_POLICIES", [])
WAN_CONFIG = getattr(config, "WAN_CONFIG", {})


class Router:
    POLICY_PRIORITY_BASE = 10000
    DEFAULT_DENY_PRIORITY = 19999

    def run(self, cmd):
        return subprocess.run(cmd, capture_output=True, text=True)

    def is_link_up(self, iface):
        try:
            with open(f"/sys/class/net/{iface}/operstate") as f:
                return f.read().strip() == "up"
        except OSError:
            return False

    def show_routes(self):
        result = self.run(["ip", "route"])
        print("[ROUTES]\n", result.stdout)

    def table_for(self, wan):
        names = list(WAN_CONFIG)
        return ROUTING_TABLE_BASE + names.index(wan)

    def clean_policy_rules(self):
        result = self.run(["ip", "rule", "show"])
        if result.returncode != 0:
            return

        for line in result.stdout.splitlines():
            if ":" not in line:
                continue
            priority = line.split(":", 1)[0].strip()
            if not priority.isdigit():
                continue
            number = int(priority)
            if self.POLICY_PRIORITY_BASE <= number < self.POLICY_PRIORITY_BASE + 1000:
                subprocess.run(["ip", "rule", "del", "priority", str(number)], stderr=subprocess.DEVNULL)
            elif number == self.DEFAULT_DENY_PRIORITY:
                subprocess.run(["ip", "rule", "del", "priority", str(number)], stderr=subprocess.DEVNULL)

    def rebuild_policy_routes(self):
        """Rebuild Linux policy-routing tables and source-subnet rules."""
        self.clean_policy_rules()

        for wan, cfg in WAN_CONFIG.items():
            table = str(self.table_for(wan))
            iface = cfg["iface"]
            gw = cfg["gw"]
            subprocess.run(["ip", "route", "flush", "table", table], stderr=subprocess.DEVNULL)
            result = self.run(["ip", "route", "replace", "default", "via", gw, "dev", iface, "table", table])
            if result.returncode != 0:
                print(f"[POLICY ROUTE ERROR] {wan}: {result.stderr.strip()}")

        for index, policy in enumerate(SUBNET_POLICIES):
            wan = policy.get("wan")
            source = policy.get("source")
            if wan not in WAN_CONFIG or not source:
                print(f"[POLICY] skipped invalid policy: {policy}")
                continue
            priority = str(self.POLICY_PRIORITY_BASE + index)
            table = str(self.table_for(wan))
            result = self.run(["ip", "rule", "add", "priority", priority, "from", source, "table", table])
            if result.returncode != 0 and "File exists" not in result.stderr:
                print(f"[POLICY RULE ERROR] {source} -> {wan}: {result.stderr.strip()}")

        if DEFAULT_POLICY == "deny":
            # Deny unmatched traffic after explicit subnet policies. Local and
            # directly connected routes still work before this rule.
            result = self.run(["ip", "rule", "add", "priority", str(self.DEFAULT_DENY_PRIORITY), "unreachable"])
            if result.returncode != 0 and "File exists" not in result.stderr:
                print(f"[DEFAULT POLICY ERROR] {result.stderr.strip()}")

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

        subprocess.run(["ip", "route", "del", "default"], stderr=subprocess.DEVNULL)

        if DEFAULT_POLICY == "allow":
            result = self.run(["ip", "route", "replace", "default", "via", gw, "dev", iface])
        else:
            result = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

        if result.returncode != 0:
            print("[ROUTER ERROR]", result.stderr.strip())
            return False

        self.rebuild_policy_routes()

        default_text = "default allowed" if DEFAULT_POLICY == "allow" else "default denied"
        print(f"[ROUTER] {wan} is now ACTIVE (via {gw} dev {iface}, {default_text})")
        return True
