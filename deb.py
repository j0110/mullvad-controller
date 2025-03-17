#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import shutil
import glob
import sys
import apt

def is_admin():
    return(os.getuid() == 0)

def install_module(module, deb):
    cache = apt.Cache()
    cache.open()
    package = cache["python3-" + deb]
    package.mark_install()
    cache.commit()

def extra_pip():
    return

def check_psexec():
    return

def unload_tunnel(tunnel):
    subprocess.run(["systemctl", "stop", "wg-quick@" + tunnel])

def load_tunnel():
    print("Loading the new tunnel.")
    os.makedirs("/etc/wireguard", exist_ok=True)
    shutil.move("mullvad.conf", "/etc/wireguard/mullvad.conf")
    subprocess.run(["systemctl", "enable", "wg-quick@mullvad"])
    subprocess.run(["systemctl", "restart", "wg-quick@mullvad"])

def write_conf(entry_server, exit_server, privkey, address):    
    with open("mullvad.conf", "w") as f:
        f.write(f"[Interface]\n")
        f.write(f"PrivateKey = {privkey}\n")
        f.write(f"Address = {address}\n")
        f.write(f"DNS = 10.64.0.1\n")
        f.write(f"PostUp = iptables -I OUTPUT ! -o %i -m mark ! --mark $(wg show %i fwmark) -m addrtype ! --dst-type LOCAL -j REJECT && ip6tables -I OUTPUT ! -o %i -m mark ! --mark $(wg show %i fwmark) -m addrtype ! --dst-type LOCAL -j REJECT\n")
        f.write(f"PostUp = \"{sys.executable}\" \"{os.path.dirname(os.path.abspath(__file__)) + os.sep}starter.py\" %i\n")
        f.write(f"PreDown = iptables -D OUTPUT ! -o %i -m mark ! --mark $(wg show %i fwmark) -m addrtype ! --dst-type LOCAL -j REJECT && ip6tables -D OUTPUT ! -o %i -m mark ! --mark $(wg show %i fwmark) -m addrtype ! --dst-type LOCAL -j REJECT\n")
        f.write(f"\n")
        f.write(f"[Peer]\n")
        f.write(f"PublicKey = {exit_server.pubkey}\n")
        f.write(f"Endpoint = {entry_server.ipv4}:{exit_server.port}\n")
        f.write(f"AllowedIPs = 0.0.0.0/0, ::/0\n")
        f.write(f"PersistentKeepalive = 25")
    return()

def install_shortcut():
    with open("/usr/share/applications/mullvad-controller.desktop", "w") as f:
        f.write(f"[Desktop Entry]\n")
        f.write(f"Type=Application\n")
        f.write(f"Name=Mullvad Controller\n")
        f.write(f"Comment=Mullvad Controller\n")
        f.write(f"Exec=gnome-terminal -e \"sudo \"{sys.executable}\" \"{os.path.dirname(os.path.abspath(__file__)) + os.sep}main.py\"\"\n")
        f.write(f"Terminal=true\n")