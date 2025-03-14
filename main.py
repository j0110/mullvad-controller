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
import json
import random
import key

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

def get_servers():
    print("Contacting Mullvad API for server list.")
    response = requests.get("https://api.mullvad.net/public/relays/wireguard/v2/")
    if response.status_code // 100 != 2:
        print("Error: Unable to connect to Mullvad API.", file=sys.stderr)
        sys.exit(1)
    with open(os.path.dirname(os.path.abspath(__file__)) + os.sep + "servers.json", "w") as servers_file:
        servers_file.write(response.text)

def load_servers():
    if not exists_servers():
        get_servers()
    with open(os.path.dirname(os.path.abspath(__file__)) + os.sep + "servers.json", "r") as servers_file:
        return(json.loads(servers_file.read()))

def select_server():
    while True :
        r = input("Would you like to choose yourself a relay or pick a random one ?\n(Y for choosing, N for random picking) > ")
        if r.lower() == "y":
            return select_server_not_random()
        if r.lower() == "n":
            return pick_random_server()

def select_server_not_random():
    server = {}

    # Group locations by country
    countries = {}
    for loc_key, loc in servers["locations"].items():
        country = loc["country"]
        if country not in countries:
            countries[country] = []
        countries[country].append((loc_key, loc))
    
    country_list = sorted(countries.keys())

    # Country selection loop
    while True:
        print("\nSelect a country:")
        for i, country in enumerate(country_list):
            print("[" + str(i).zfill(2) + "] " + country)
        country_input = input("Enter the number of the desired country > ").strip()
        try:
            country_choice = int(country_input)
            if 0 <= country_choice < len(country_list):
                selected_country = country_list[country_choice]
                server["country"] = selected_country
                print(selected_country + " selected.")
            else:
                print("Invalid selection. Try again.")
                continue
        except ValueError:
            print("Please enter a valid number.")
            continue

        # City selection loop for the chosen country
        while True:
            print("\nSelect a city in " + server["country"] + ":")
            locations_in_country = countries[server["country"]]
            for i, (loc_key, loc_servers) in enumerate(locations_in_country):
                print("[" + str(i).zfill(2) + "] " + loc_servers["city"])
            print("[B] Go back to country selection")
            city_input = input("Enter the number of the desired city or 'B' to go back > ").strip()
            if city_input.lower() == "b":
                print("Going back to country selection.")
                break  # Back to country selection
            try:
                city_choice = int(city_input)
                if 0 <= city_choice < len(locations_in_country):
                    selected_loc_key, selected_loc = locations_in_country[city_choice]
                    server["city"] = selected_loc["city"]
                    server["latitude"] = selected_loc["latitude"]
                    server["longitude"] = selected_loc["longitude"]
                    current_location_key = selected_loc_key  # used for filtering relays
                    print(selected_loc["city"] + " selected.")
                else:
                    print("Invalid selection. Try again.")
                    continue
            except ValueError:
                print("Please enter a valid number or 'B' to go back.")
                continue

            # Relay selection loop for the chosen city
            while True:
                print("\nSelect a relay in " + server["city"] + ", " + server["country"] + ":")
                # Only include relays that are active
                available_relays = [
                    relay for relay in servers["wireguard"]["relays"]
                    if relay["location"] == current_location_key and relay["active"] == True
                ]
                if not available_relays:
                    print("No active relays available for this location.")
                    back_input = input("Press 'B' to go back to city selection > ").strip()
                    if back_input.lower() == "b":
                        break  # Back to city selection
                    else:
                        continue
                for i, relay in enumerate(available_relays):
                    owned_str = " (Owned)" if relay.get("owned", False) else " (Not owned)"
                    print("[" + str(i).zfill(2) + "] " + relay["hostname"] + owned_str)
                print("[B] Go back to city selection")
                relay_input = input("Enter the number of the desired relay or 'B' to go back > ").strip()
                if relay_input.lower() == "b":
                    print("Going back to city selection.")
                    break  # Back to city selection loop
                try:
                    relay_choice = int(relay_input)
                    if 0 <= relay_choice < len(available_relays):
                        selected_relay = available_relays[relay_choice]
                        server["hostname"] = selected_relay["hostname"]
                        server["ipv4"] = selected_relay["ipv4_addr_in"]
                        server["ipv6"] = selected_relay["ipv6_addr_in"]
                        server["pubkey"] = selected_relay["public_key"]
                        server["owned"] = selected_relay["owned"]
                        owned_text = "Owned" if selected_relay["owned"] else "Not owned"
                        print(selected_relay["hostname"] + " selected. (" + owned_text + ")")
                        return server  # Final selection complete
                    else:
                        print("Invalid selection. Try again.")
                        continue
                except ValueError:
                    print("Please enter a valid number or 'B' to go back.")
                    continue
            # End of relay selection loop.
            # If the user went back from relay selection, they remain in the city selection loop.
        # End of city selection loop.
        # If the user went back from city selection, they remain in the country selection loop.

def pick_random_server():
    # Filter only active relays
    relays = [relay for relay in servers["wireguard"]["relays"] if relay["active"] == True]
    if not relays:
        print("No active relays found.")
        return None

    # Ask about owned preference
    owned_choice = input("Do you care if the server is owned? (Y for only owned, Enter for no preference) > ").strip().lower()
    if owned_choice == "y":
        relays = [r for r in relays if r["owned"] == True]

    if not relays:
        print("No relays match the owned filter.")
        return None

    # Ask user if they want to select a specific country.
    country_filter_choice = input("Do you want to select a specific country? (Y for yes, Enter for no) > ").strip().lower()
    if country_filter_choice == "y":
        # Create a sorted list of available countries based on the filtered relays
        available_countries = sorted({servers["locations"][r["location"]]["country"] 
                                      for r in relays if r["location"] in servers["locations"]})
        print("Available countries:")
        for idx, country in enumerate(available_countries):
            print(f"[{idx:02}] {country}")
        try:
            country_idx = int(input("Enter the number corresponding to the desired country > ").strip())
            if 0 <= country_idx < len(available_countries):
                chosen_country = available_countries[country_idx].lower()
                relays = [r for r in relays if servers["locations"].get(r["location"], {}).get("country", "").lower() == chosen_country]
            else:
                print("Invalid selection. No country filter will be applied.")
        except ValueError:
            print("Invalid input. No country filter will be applied.")
    else:
        # If no country filter is selected, display all available countries matching user preference.
        available_countries = sorted({servers["locations"][r["location"]]["country"] 
                                      for r in relays if r["location"] in servers["locations"]})
        print("Relays available in the following countries:")
        for country in available_countries:
            print("- " + country)

    if not relays:
        print("No relays match the selected filters.")
        return None

    # Random selection loop: pick a random server and ask for confirmation.
    while True:
        selected_relay = random.choice(relays)
        loc_info = servers["locations"].get(selected_relay["location"], {})
        server = {
            "hostname": selected_relay["hostname"],
            "ipv4": selected_relay["ipv4_addr_in"],
            "ipv6": selected_relay["ipv6_addr_in"],
            "pubkey": selected_relay["public_key"],
            "owned": selected_relay["owned"],
            "country": loc_info.get("country", ""),
            "city": loc_info.get("city", ""),
            "latitude": loc_info.get("latitude", None),
            "longitude": loc_info.get("longitude", None)
        }
        print("\nRandom server selected:")
        for k in ["hostname", "country", "city", "owned"]:
            print(f"\t{k.capitalize()} : {server[k]}")
        confirmation = input("Is this server acceptable? (Y to accept, any other key to pick another) > ").strip().lower()
        if confirmation == "y":
            return server

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

def exists_servers():
    return(os.path.isfile(os.path.dirname(os.path.abspath(__file__)) + os.sep + "servers.json"))

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
    print()
    if ask_multihop():
        print("Please select an entry server :")
        entry_server = select_server()
        print()
        print("Please select an exit server :")
        exit_server = select_server()
    else:
        print("Please select a server :")
        entry_server = select_server()
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
    servers = load_servers()

    while True:
        print()
        detect_active_connection()
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
            get_servers()
            servers = load_servers()
        if answer == "5":
            update()
            print("Please restart the script to apply update.")
            input("Press ENTER to exit.")
            sys.exit(0)
        if answer == "6":
            install_shortcut()