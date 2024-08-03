#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import subprocess
import platform
import os.path
import io
import zipfile
import glob
import stat

if platform.system() == "Windows":
    from win import *
elif platform.system() == "Linux":
    from deb import *
else:
    print("Error : You are not on a supported platform, exiting.")
    sys.exit(1)

if not is_admin():
    print("You are not running this script with admin/su rights.")
    print("Please restart with admin/su rights.")
    print("Bye !")
    sys.exit(0)

try:
    import requests
except ModuleNotFoundError:
    print("Installing requests...")
    subprocess.run([sys.executable, "-m", "pip", "install", "requests"], check=True)
    import requests

try:
    import git
except ModuleNotFoundError:
    print("Installing GitPython...")
    subprocess.run([sys.executable, "-m", "pip", "install", "GitPython"], check=True)
    import git

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
    return(os.path.isfile(os.path.dirname(os.path.abspath(__file__)) + os.sep + "key"))

def write_key(account, privkey):
    with open(os.path.dirname(os.path.abspath(__file__)) + os.sep + "key", "w") as key_file:
        key_file.write("\n".join([account, privkey]))

def load_key():
    with open(os.path.dirname(os.path.abspath(__file__)) + os.sep + "key", "r") as key_file:
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

def check_mvup():
    print("Checking if mullvad-upgrade-tunnel executable is present.")
    for file in glob.glob(os.path.dirname(os.path.abspath(__file__)) + os.sep + "*"):
        if file.split(os.sep)[-1].startswith("mullvad-upgrade-tunnel"):
            print("mullvad-upgrade-tunnel is present, skipping downloading it.")
            # TODO : check it with .asc file
            return
    print("Downloading mullvad-upgrade-tunnel using Github servers.")
    api_response = requests.get("https://api.github.com/repos/mullvad/wgephemeralpeer/releases/latest")
    if api_response.status_code // 100 != 2:
        print("Error: Unable to connect to Github API.", file=sys.stderr)
        sys.exit(1)
    version = api_response.json()['tag_name']

    zip_response = requests.get(f"https://github.com/mullvad/wgephemeralpeer/releases/download/{version}/mullvad-upgrade-tunnel_{version}_{platform.system().lower()}_amd64.zip")
    if zip_response.status_code // 100 != 2:
        print("Error: Unable to connect to Github API.", file=sys.stderr)
        sys.exit(1)
    zip_file = io.BytesIO(zip_response.content)
    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        zip_ref.extractall(os.path.dirname(os.path.abspath(__file__)))
    if platform.system() == "Linux":
        file_path = os.path.dirname(os.path.abspath(__file__)) + os.sep + "mullvad-upgrade-tunnel"
        new_permissions = os.stat(file_path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        os.chmod(file_path, new_permissions)

def update():
    g = git.cmd.Git(os.path.dirname(os.path.abspath(__file__)))
    g.pull()

def main():
    detect_active_connection()
    while True:
        check_mvup()
        print("Which action would you like to perform :")
        print("[0] Quit")
        print("[1] Connect to a new tunnel")
        print("[2] Disconnect the existing tunnel")
        print("[3] Update this script (using GitHub servers)")
        answer = input("Which action would you like to perform > ").strip()
        if answer == "0":
            print("Bye !")
            return()
        if answer == "1":
            connect()
        if answer == "2":
            disconnect()
        if answer == "3":
            update()

if __name__ == '__main__':
    main()