import subprocess


class Router:

    def is_link_up(self, iface):
        try:
            with open(f"/sys/class/net/{iface}/operstate") as f:
                return f.read().strip() == "up"
        except:
            return False

    def show_routes(self):
        result = subprocess.run(["ip", "route"], capture_output=True, text=True)
        print("[ROUTES]\n", result.stdout)

    def switch(self, wan):

        print(f"[ROUTER] switching to {wan}")

        if wan == "WAN1":
            iface = "enp10s0"
            gw = "192.168.4.254"

        elif wan == "WAN2":
            iface = "enp11s0"
            gw = "192.168.201.1"

        else:
            print("[ROUTER] invalid WAN")
            return False

        if not self.is_link_up(iface):
            print(f"[ROUTER] {wan} interface DOWN")
            return False

        # FORCE CLEAN STATE
        subprocess.run(["ip", "route", "del", "default"], stderr=subprocess.DEVNULL)

        # ADD ROUTE (fail visible)
        result = subprocess.run([
            "ip", "route", "add", "default",
            "via", gw,
            "dev", iface
        ], capture_output=True, text=True)

        if result.returncode != 0:
            print("[ROUTER ERROR]", result.stderr)
            return False

        print(f"[ROUTER] {wan} ACTIVE")

        self.show_routes()

        return True
