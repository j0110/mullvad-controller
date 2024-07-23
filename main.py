#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import requests
import subprocess
import platform
import os.path

if platform.system() == "Windows":
    from windows import *
elif platform.system() == "Linux":
    from linux import *
else:
    print("Error : You are not on a supported platform, exiting.")
    sys.exit(1)

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

def ask_multihop():
    while True:
        answer = input("Would you like to use a different exit server than the entry server ? [y/n] > ").strip().lower()
        if answer == "y":
            return(True)
        if answer == "n":
            return(False)

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
    disconnect()
    load_tunnel(conf_name)

def get_active_tunnel():
    return(subprocess.run(['wg', 'show', 'all', 'dump'], capture_output=True, text=True).stdout.split("\t")[0])

def detect_active_connection():
    active_tunnel = get_active_tunnel()
    if active_tunnel:
        print("You are actually connected to " + active_tunnel + ".")
    else:
        print("You are not actually connected to a Wireguard server.")

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

if __name__ == '__main__':
    main()