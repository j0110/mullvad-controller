import subprocess
from servers import Servers

class Tunnel():
    def __init__(self):
        self.servers = Servers()
        self.refresh()

    def refresh(self):
        dump = self.dump_tunnel()
        self.name = dump[0]
        self.pubkey = dump[5]
        self.tunnel = self.recognize_tunnel()
        self.recognition = self.detect_active_connection()

    def dump_tunnel(self):
        return(subprocess.run(['wg', 'show', 'all', 'dump'], capture_output=True, text=True).stdout.split("\t"))

    def recognize_tunnel(self):
        for relay in self.servers.servers["wireguard"]["relays"]:
            if relay["public_key"] == self.pubkey:
                loc_info = self.servers.servers["locations"].get(relay["location"], {})
                server = {
                    "hostname": relay["hostname"],
                    "ipv4": relay["ipv4_addr_in"],
                    "ipv6": relay["ipv6_addr_in"],
                    "pubkey": relay["public_key"],
                    "owned": relay["owned"],
                    "country": loc_info.get("country", ""),
                    "city": loc_info.get("city", ""),
                    "latitude": loc_info.get("latitude", None),
                    "longitude": loc_info.get("longitude", None)
                }
                return server

    def detect_active_connection(self):
        if self.name:
            if self.tunnel:
                return(f"You are actually connected to {self.tunnel['hostname']} in {self.tunnel['city']}, {self.tunnel['country']} (Mullvad tunnel).")
            else:
                return(f"You are actually connected to {self.name} (not a Mullvad tunnel).")
        else:
            return("You are not actually connected to a Wireguard server.")