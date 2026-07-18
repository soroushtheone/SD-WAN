import subprocess


class Marker:

    def set_voip_wan(self, wan):

        mark = "1" if wan == "WAN1" else "2"

        print(f"[MARKER] VoIP → {wan} (mark {mark})")

        # delete old rule (safe even if not exists)
        subprocess.run([
            "iptables", "-t", "mangle", "-D", "PREROUTING",
            "-p", "udp", "--dport", "5060",
            "-j", "MARK", "--set-mark", "1"
        ], stderr=subprocess.DEVNULL)

        subprocess.run([
            "iptables", "-t", "mangle", "-D", "PREROUTING",
            "-p", "udp", "--dport", "5060",
            "-j", "MARK", "--set-mark", "2"
        ], stderr=subprocess.DEVNULL)

        # add new rule
        subprocess.run([
            "iptables", "-t", "mangle", "-A", "PREROUTING",
            "-p", "udp", "--dport", "5060",
            "-j", "MARK", "--set-mark", mark
        ])
