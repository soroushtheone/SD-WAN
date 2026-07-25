# System Requirements

Install these before running the SD-WAN controller on a Linux device.

## Debian / Ubuntu

```bash
sudo apt update
sudo apt install -y python3 iproute2 iputils-ping isc-dhcp-client systemd
sudo modprobe 8021q
```

## RHEL / CentOS / Fedora

```bash
sudo dnf install -y python3 iproute iputils dhcp-client systemd
sudo modprobe 8021q
```

If your system uses `yum` instead of `dnf`:

```bash
sudo yum install -y python3 iproute iputils dhcp-client systemd
sudo modprobe 8021q
```

## Required Commands

- `python3`: runs the controller.
- `ip`: configures interfaces, default routes, policy rules, and routing tables.
- `ping`: checks WAN latency, jitter, and packet loss.
- `dhclient`: required only for WAN interfaces configured with DHCP.
- `systemctl`: required only when running the controller as a service.
- `8021q` kernel module: required for VLAN interfaces.

## Permissions

Run the controller as root because it changes IP addresses and routes:

```bash
sudo python3 setup_wizard.py
sudo python3 main.py
```
