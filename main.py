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
import key
from servers import Servers
from tunnel import Tunnel

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
    install_module("requests")
    import requests

try:
    import git
except ModuleNotFoundError:
    print("Installing GitPython...")
    install_module("GitPython", "git")
    import git

extra_pip()

def get_account():
    return(input("Please enter your Mullvad account number > ").strip())

def get_privkey():
    return(input("Please enter your Mullvad private key > ").strip())

def get_pubkey(privkey):
    return(subprocess.run(['wg', 'pubkey'], input=privkey, capture_output=True, text=True).stdout.strip())

def get_address(account, pubkey):
    print("Contacting Mullvad API for private address.")
    response = requests.post("https://api.mullvad.net/wg", servers={'account': account, 'pubkey': pubkey})
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

def write_key(account, privkey, address):
    with open(os.path.dirname(os.path.abspath(__file__)) + os.sep + "key", "w") as key_file:
        key_file.write("\n".join([account, privkey, address]))

def load_key():
    if not exists_key():
        account = get_account()
        privkey = get_privkey()
        pubkey = get_pubkey(privkey)
        address = get_address(account, pubkey)
        key.write_key(account, privkey, address)
        return(account, privkey, address)
    else:
        return(key.load_key())
    
def show_key():
    if not exists_key():
        print("No key registered.")
    else:
        account, privkey, address = load_key()
        print(f"\tAccount number : {account}")
        print(f"\tPrivate key : {privkey}")
        print(f"\tAddress : {address}")

def reload_tunnel(conf_name):
    print("Preparing to load the newly created tunnel.")
    disconnect()
    load_tunnel(conf_name)

def disconnect():
    active_tunnel.refresh()
    active_tunnel = active_tunnel.name
    if active_tunnel:
        unload_tunnel(active_tunnel)
    delete_extra_tunnels()

def connect():
    print()
    if ask_multihop():
        print("Please select an entry server :")
        entry_server = servers.select_server()
        print()
        print("Please select an exit server :")
        exit_server = servers.select_server()
    else:
        print("Please select a server :")
        entry_server = servers.select_server()
        exit_server = None
    print()
    print("Writing configuration file.")
    conf_name = write_conf(entry_server, exit_server, *load_key()[1:])
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
    print(git.cmd.Git(os.path.dirname(os.path.abspath(__file__))).pull())
    print("\n")

if __name__ == '__main__':
    
    check_mvup()
    check_psexec()
    servers = Servers()
    active_tunnel = Tunnel()

    while True:
        print()
        active_tunnel.refresh()
        print(active_tunnel.recognition)
        print()
        print("[0] Quit")
        print("[1] Connect to a new tunnel")
        print("[2] Disconnect the existing tunnel")
        print("[3] Show personal key")
        print("[4] Update the relays list (using Mullvad servers)")
        print("[5] Update this script (using GitHub servers)")
        print("[6] Install a beautiful shortcut")
        answer = input("Which action would you like to perform > ").strip()
        if answer == "0":
            print("Bye !")
            sys.exit(0)
        if answer == "1":
            connect()
        if answer == "2":
            disconnect()
        if answer == "3":
            show_key()
        if answer == "4":
            servers.update_servers()
            active_tunnel.servers.load_servers()
        if answer == "5":
            update()
            print("Please restart the script to apply update.")
            input("Press ENTER to exit.")
            sys.exit(0)
        if answer == "6":
            install_shortcut()