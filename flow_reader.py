import subprocess

def get_flows():
    result = subprocess.run(
        ["conntrack", "-L"],
        capture_output=True,
        text=True
    )

    flows = []

    for line in result.stdout.splitlines():

        if "udp" in line or "tcp" in line:

            if "dport=" in line:
                try:
                    parts = line.split()

                    for p in parts:
                        if "dport=" in p:
                            port = int(p.split("=")[1])
                            flows.append({"port": port})
                except:
                    continue

    return flows
