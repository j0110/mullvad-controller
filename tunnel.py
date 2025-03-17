#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
from servers import Servers
from server import Server

class Tunnel():
    def __init__(self, servers):
        self.refresh(servers)

    def refresh(self, servers):
        dump = self.dump_tunnel()
        self.name = dump[0]
        self.pubkey = dump[5]
        self.tunnel = self.recognize_tunnel(servers)
        self.recognition = self.detect_active_connection()

    def dump_tunnel(self):
        return(subprocess.run(['wg', 'show', 'all', 'dump'], capture_output=True, text=True).stdout.split("\t"))

    def recognize_tunnel(self, servers):
        return Server(servers, self.pubkey)

    def detect_active_connection(self):
        if self.name:
            if self.tunnel.mullvad:
                return(f"You are actually connected to {self.tunnel.name} in {self.tunnel.city}, {self.tunnel.country} (Mullvad tunnel).")
            else:
                return(f"You are actually connected to {self.name} (not a Mullvad tunnel).")
        else:
            return("You are not actually connected to a Wireguard server.")