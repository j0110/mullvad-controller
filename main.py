#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import requests
import subprocess
import platform
import os
import glob
import shutil

def get_servers():
    print("Contacting Mullvad API for server list.")
    response = requests.get("https://api.mullvad.net/public/relays/wireguard/v1/")
    if response.status_code // 100 != 2:
        print("Error: Unable to connect to Mullvad API.", file=sys.stderr)
        sys.exit(1)
    return(response.json())

def select_server(servers):
    server = {}

    print(f"Select a country :")
    for i, country in enumerate(servers["countries"]):
        print("[" + str(i).zfill(2) + "] " + country["name"])
    country = int(input("Enter the desired country > ").strip())
    server["country.name"] = servers["countries"][country]["name"]
    server["country.code"] = servers["countries"][country]["code"]
    print(server["country.name"] + " selected.")

    print(f"Select a city in {server['country.name']} :")
    for i, city in enumerate(servers["countries"][country]["cities"]):
        print("[" + str(i).zfill(2) + "] " + city["name"])
    city = int(input("Enter the desired city > ").strip())
    server["city.name"] = servers["countries"][country]["cities"][city]["name"]
    server["city.code"] = servers["countries"][country]["cities"][city]["code"]
    server["latitude"] = servers["countries"][country]["cities"][city]["latitude"]
    server["longitude"] = servers["countries"][country]["cities"][city]["longitude"]
    print(server["city.name"] + " selected.")

    print(f"Select a relay in {server['city.name']}, {server['country.name']} :")
    for i, relay in enumerate(servers["countries"][country]["cities"][city]["relays"]):
        print("[" + str(i).zfill(2) + "] " + relay["hostname"])
    relay = int(input("Enter the desired relay > ").strip())
    server["hostname"] = servers["countries"][country]["cities"][city]["relays"][relay]["hostname"]
    server["ip4"] = servers["countries"][country]["cities"][city]["relays"][relay]["ipv4_addr_in"]
    server["ip6"] = servers["countries"][country]["cities"][city]["relays"][relay]["ipv6_addr_in"]
    server["port"] = servers["countries"][country]["cities"][city]["relays"][relay]["multihop_port"]
    server["pubkey"] = servers["countries"][country]["cities"][city]["relays"][relay]["public_key"]
    print(server["hostname"] + " selected.")

    return(server)

def get_account():
    return(input("Please enter your Mullvad account number > ").strip())

def get_privkey():
    return(input("Please enter your Mullvad private key > ").strip())

def get_pubkey(privkey):
    return(subprocess.run(['wg', 'pubkey'], input=privkey, capture_output=True, text=True).stdout.strip())

def get_address(account, pubkey):
    print("Contacting Mullvad API for private address.")
    response = requests.post("https://api.mullvad.net/wg", data={'account': account, 'pubkey': pubkey})
    if response.status_code // 100 != 2 :
        print("Error: " + response.text, file=sys.stderr)
        sys.exit(1)
    address = response.text.strip()
    if not address:
        print("Error: " + response.text, file=sys.stderr)
        sys.exit(1)
    return(address)

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
        if platform.system() == "Linux":
            f.write(f"PostUp = iptables -I OUTPUT ! -o %i -m mark ! --mark $(wg show %i fwmark) -m addrtype ! --dst-type LOCAL -j REJECT && ip6tables -I OUTPUT ! -o %i -m mark ! --mark $(wg show %i fwmark) -m addrtype ! --dst-type LOCAL -j REJECT\n")
            f.write(f"PostUp = mullvad-upgrade-tunnel -wg-interface %i\n")
            f.write(f"PreDown = iptables -D OUTPUT ! -o %i -m mark ! --mark $(wg show %i fwmark) -m addrtype ! --dst-type LOCAL -j REJECT && ip6tables -D OUTPUT ! -o %i -m mark ! --mark $(wg show %i fwmark) -m addrtype ! --dst-type LOCAL -j REJECT\n")
        if platform.system() == "Windows":
            f.write(f"PostUp = mullvad-upgrade-tunnel -wg-interface %WIREGUARD_TUNNEL_NAME%\n")
        f.write(f"\n")
        f.write(f"[Peer]\n")
        f.write(f"PublicKey = {entry_server['pubkey']}\n")
        f.write(f"Endpoint = {entry_server['ip4']}:{exit_server['port']}\n")
        f.write(f"AllowedIPs = 0.0.0.0/0, ::/0\n")
        f.write(f"PersistentKeepalive = 25")
    return(config_file)

def ask_multihop():
    while True:
        answer = input("Would you like to use a different exit server than the entry server ? [y/n] > ").strip().lower()
        if answer == "y":
            return(True)
        if answer == "n":
            return(False)

def is_admin():
    if platform.system() == "Windows":
        import ctypes
        return(ctypes.windll.shell32.IsUserAnAdmin() == 1)
    if platform.system() == "Linux":
        return(os.getuid() == 0)

def exists_key():
    return(os.path.isfile("key"))

def write_key(account, privkey):
    with open("key", "w") as key_file:
        key_file.write("\n".join([account, privkey]))

def load_key():
    with open("key", "r") as key_file:
        return(key_file.read().split("\n"))

def reload_tunnel(conf_name):
    print("Preparing to load the newly created tunnel.")
    if platform.system() == "Windows":
        write_registry_key()
    disconnect()
    load_tunnel(conf_name)

def write_registry_key():
    print("Writing key in the registry.")
    cmd = subprocess.run(["reg", "add", "HKLM\\Software\\WireGuard", "/v", "DangerousScriptExecution", "/t", "REG_DWORD", "/d", "1", "/f"])
    print(cmd.returncode)
    if cmd.returncode == "0":
        print("Error: Unable to write key in the registry.", file=sys.stderr)
        sys.exit(1)

def get_active_tunnel():
    return(subprocess.run(['wg', 'show', 'all', 'dump'], capture_output=True, text=True).stdout.split("\t")[0])

def unload_tunnel(tunnel):
    print("Unloading active tunnel : " + tunnel + ".")
    if platform.system() == "Windows":
        subprocess.run(["wireguard", "/uninstalltunnelservice", tunnel])
    if platform.system() == "Linux":
        subprocess.run(["systemctl", "stop", f"wg-quick@{tunnel}"])

def delete_extra_tunnels():
    print("Deleting older tunnels.")
    if platform.system() == "Windows":
        path = "C:\\Program Files\\WireGuard\\Data\\mullvad\\"
        [subprocess.run(["wireguard", "/uninstalltunnelservice", file]) for file in glob.glob(path + "*") if file.split(os.sep)[-1].startswith("m_")]
    if platform.system() == "Linux":
        path = "/etc/wireguard/"
        [subprocess.run(["systemctl", "disable", f"wg-quick@{file.split(os.sep)[-1]}"]) for file in glob.glob(path + "*") if file.split(os.sep)[-1].startswith("m_")]
    [os.remove(file) for file in glob.glob(path + "*") if file.split(os.sep)[-1].startswith("m_")]

def load_tunnel(conf_name):
    print("Loading the new tunnel.")
    if platform.system() == "Windows":
        os.makedirs("C:\\Program Files\\WireGuard\\Data\\mullvad", exist_ok=True)
        shutil.move(conf_name, "C:\\Program Files\\WireGuard\\Data\\mullvad\\" + conf_name)
        subprocess.run(["wireguard", "/installtunnelservice", "C:\\Program Files\\WireGuard\\Data\\mullvad\\" + conf_name])
    if platform.system() == "Linux":
        os.makedirs("/etc/wireguard", exist_ok=True)
        shutil.move(conf_name, "/etc/wireguard/" + conf_name)
        subprocess.run(["systemctl", "start", f"wg-quick@{conf_name}"])

def detect_active_connection():
    active_tunnel = get_active_tunnel()
    if active_tunnel:
        print("You are actually connected to " + active_tunnel + ".")
    else:
        print("You are not actually connected to a Wireguard server.")

def main():
    detect_active_connection()
    if not is_admin():
        print("You are not running this script with admin/su rights.")
        print("Please restart with admin/su rights.")
        print("Bye !")
        sys.exit(0)
    while True:
        print("Which action would you like to perform :")
        print("[0] Connect to a new tunnel")
        print("[1] Disconnect the existing tunnel")
        answer = input("Which action would you like to perform > ").strip()
        if answer == "0":
            connect()
            return()
        if answer == "1":
            disconnect()
            return()

def disconnect():
    active_tunnel = get_active_tunnel()
    if active_tunnel:
        print(active_tunnel)
        unload_tunnel(active_tunnel)
    delete_extra_tunnels()

def connect():
    if not exists_key():
        account = get_account()
        privkey = get_privkey()
        write_key(account, privkey)
    else:
        account, privkey = load_key()
    pubkey = get_pubkey(privkey)
    servers = get_servers()
    address = get_address(account, pubkey)
    print()
    if ask_multihop():
        print("Please select an entry server :")
        entry_server = select_server(servers)
        print()
        print("Please select an exit server :")
        exit_server = select_server(servers)
    else:
        print("Please select a server :")
        entry_server = select_server(servers)
        exit_server = None
    print()
    print("Writing configuration file.")
    conf_name = write_conf(entry_server, exit_server, privkey, address)
    reload_tunnel(conf_name)

if __name__ == '__main__':
    main()