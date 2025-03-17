#!/usr/bin/env python3
# -*- coding: utf-8 -*-

class Server():
    def __init__(self, servers, id):
        self.mullvad = False
        if len(id) == 44:
            key = "public_key"
        else:
            key = "hostname"
        for relay in servers["wireguard"]["relays"]:
            if relay[key] == id:
                loc_info = servers["locations"][relay["location"]]
                self.name = relay["hostname"]
                self.ipv4 = relay["ipv4_addr_in"]
                self.ipv6 = relay["ipv6_addr_in"]
                self.pubkey = relay["public_key"]
                self.owned = relay["owned"]
                self.country = loc_info["country"]
                self.city = loc_info["city"]
                self.latitude = loc_info["latitude"]
                self.longitude = loc_info["longitude"]
                self.mullvad = True

class VoidServer():
    def __init__(self, entry_server):
        self.port = "51820"
        self.pubkey = entry_server.pubkey