#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import requests
import random
from server import Server, VoidServer

class Servers():
    def __init__(self):
        self.load_servers()

    def exists_servers(self):
        return(os.path.isfile(os.path.dirname(os.path.abspath(__file__)) + os.sep + "servers.json"))

    def load_servers(self):
        if not self.exists_servers():
            self.get_servers()
        with open(os.path.dirname(os.path.abspath(__file__)) + os.sep + "servers.json", "r") as servers_file:
            self.servers = json.loads(servers_file.read())

    def get_servers(self):
        print("Contacting Mullvad API for server list.")
        response = requests.get("https://api.mullvad.net/public/relays/wireguard/v2/")
        if response.status_code // 100 != 2:
            print("Error: Unable to connect to Mullvad API.", file=sys.stderr)
            sys.exit(1)
        with open(os.path.dirname(os.path.abspath(__file__)) + os.sep + "servers.json", "w") as servers_file:
            servers_file.write(response.text)

    def update_servers(self):
        self.get_servers()
        self.load_servers()

    def select_server(self):
        while True :
            r = input("Would you like to choose yourself a relay or pick a random one ?\n(Y for choosing, N for random picking) > ")
            if r.lower() == "y":
                return self.select_server_not_random()
            if r.lower() == "n":
                return self.pick_random_server()

    def select_server_not_random(self):
        server = {}

        # Group locations by country
        countries = {}
        for loc_key, loc in self.servers["locations"].items():
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
                        relay for relay in self.servers["wireguard"]["relays"]
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
                            server = Server(self.servers, available_relays[relay_choice]["hostname"])
                            if self.ask_server_ok(server):
                                return server
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

    def pick_random_server(self):
        # Filter only active relays
        relays = [relay for relay in self.servers["wireguard"]["relays"] if relay["active"] == True]
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
            available_countries = sorted({self.servers["locations"][r["location"]]["country"] 
                                        for r in relays if r["location"] in self.servers["locations"]})
            print("Available countries:")
            for idx, country in enumerate(available_countries):
                print(f"[{idx:02}] {country}")
            try:
                country_idx = int(input("Enter the number corresponding to the desired country > ").strip())
                if 0 <= country_idx < len(available_countries):
                    chosen_country = available_countries[country_idx].lower()
                    relays = [r for r in relays if self.servers["locations"].get(r["location"], {}).get("country", "").lower() == chosen_country]
                else:
                    print("Invalid selection. No country filter will be applied.")
            except ValueError:
                print("Invalid input. No country filter will be applied.")
        else:
            # If no country filter is selected, display all available countries matching user preference.
            available_countries = sorted({self.servers["locations"][r["location"]]["country"] 
                                        for r in relays if r["location"] in self.servers["locations"]})
            print("Relays available in the following countries:")
            for country in available_countries:
                print("- " + country)

        if not relays:
            print("No relays match the selected filters.")
            return None

        # Random selection loop: pick a random server and ask for confirmation.
        while True:
            selected_relay = random.choice(relays)
            server = Server(self.servers, selected_relay["hostname"])
            if self.ask_server_ok(server):
                return server

    def return_void(self, entry_server):
        return VoidServer(entry_server)

    def ask_server_ok(self, server):
        print(f"Server selected:")
        print(f"\tHostname : {server.name}")
        print(f"\tCountry : {server.country}")
        print(f"\tCity : {server.city}")
        print(f"\tOwned : {server.owned}")
        confirmation = input("Is this server acceptable? (Y to accept, any other key to pick another) > ").strip().lower()
        if confirmation == "y":
            return server