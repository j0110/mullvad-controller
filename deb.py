#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import shutil
import glob

def is_admin():
    return(os.getuid() == 0)

def unload_tunnel(tunnel):
    subprocess.run(["systemctl", "stop", "wg-quick@" + tunnel])

def delete_extra_tunnels():
    print("Deleting older tunnels.")
    path = "/etc/wireguard/"
    [subprocess.run(["systemctl", "disable", f"wg-quick@{file.split(os.sep)[-1][:-5]}"]) for file in glob.glob(path + "*") if file.split(os.sep)[-1].startswith("m_")]
    [os.remove(file) for file in glob.glob(path + "*") if file.split(os.sep)[-1].startswith("m_")]

def load_tunnel(conf_name):
    print("Loading the new tunnel.")
    os.makedirs("/etc/wireguard", exist_ok=True)
    shutil.move(conf_name, "/etc/wireguard/" + conf_name)
    subprocess.run(["systemctl", "start", "wg-quick@" + conf_name[:-5]])

def write_conf(entry_server, exit_server, privkey, address):    
    if not exit_server:
        exit_server = {"port" : "51820"}
        config_file = f"m_{entry_server['country.code'].upper()}.{entry_server['city.code']}.conf"
    else:
        config_file = f"m_{entry_server['country.code'].upper()}.{entry_server['city.code']}-{exit_server['country.code'].upper()}.{exit_server['city.code']}.conf"
    with open(config_file, "w") as f:
        f.write(f"[Interface]\n")
        f.write(f"PrivateKey = {privkey}\n")
        f.write(f"Address = {address}\n")
        f.write(f"DNS = 10.64.0.1\n")
        f.write(f"PostUp = iptables -I OUTPUT ! -o %i -m mark ! --mark $(wg show %i fwmark) -m addrtype ! --dst-type LOCAL -j REJECT && ip6tables -I OUTPUT ! -o %i -m mark ! --mark $(wg show %i fwmark) -m addrtype ! --dst-type LOCAL -j REJECT\n")
        f.write(f"PostUp = \"{sys.executable}\" \"{os.path.dirname(os.path.abspath(__file__)) + os.sep}starter.py\"\n")
        f.write(f"PreDown = iptables -D OUTPUT ! -o %i -m mark ! --mark $(wg show %i fwmark) -m addrtype ! --dst-type LOCAL -j REJECT && ip6tables -D OUTPUT ! -o %i -m mark ! --mark $(wg show %i fwmark) -m addrtype ! --dst-type LOCAL -j REJECT\n")
        f.write(f"\n")
        f.write(f"[Peer]\n")
        f.write(f"PublicKey = {entry_server['pubkey']}\n")
        f.write(f"Endpoint = {entry_server['ip4']}:{exit_server['port']}\n")
        f.write(f"AllowedIPs = 0.0.0.0/0, ::/0\n")
        f.write(f"PersistentKeepalive = 25")
    return(config_file)