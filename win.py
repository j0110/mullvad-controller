#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import ctypes
import os
import subprocess
import shutil
import glob
import sys
import winreg
import pythoncom
from win32com.shell import shell

def is_admin():
    return(ctypes.windll.shell32.IsUserAnAdmin() == 1)

def install_module(module, deb=None):
    subprocess.run([sys.executable, "-m", "pip", "install", module], check=True)

def write_registry_key():
    print("Writing key in the registry.")
    try:
        registry_path = r"Software\WireGuard"
        key_name = "DangerousScriptExecution"
        key_value = 1
        
        with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, registry_path) as key:
            winreg.SetValueEx(key, key_name, 0, winreg.REG_DWORD, key_value)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

def unload_tunnel(tunnel):
    subprocess.run(["wireguard", "/uninstalltunnelservice", tunnel])

def delete_extra_tunnels():
    print("Deleting older tunnels.")
    path = "C:\\Program Files\\WireGuard\\Data\\Configurations\\"
    [subprocess.run(["wireguard", "/uninstalltunnelservice", file]) for file in glob.glob(path + "*") if file.split(os.sep)[-1].startswith("m_")]
    [os.remove(file) for file in glob.glob(path + "*") if file.split(os.sep)[-1].startswith("m_")]

def load_tunnel(conf_name):
    write_registry_key()
    print("Loading the new tunnel.")
    shutil.move(conf_name, "C:\\Program Files\\WireGuard\\Data\\Configurations\\" + conf_name)
    subprocess.run(["wireguard", "/installtunnelservice", "C:\\Program Files\\WireGuard\\Data\\Configurations\\" + conf_name + ".dpapi"])
    subprocess.run(["sc", "config", "WireguardTunnel$" + conf_name[:-5], "start=auto"])
    subprocess.run(["sc", "failure", "WireguardTunnel$" + conf_name[:-5], "reset=0", "actions=restart/0/restart/0/restart/0"])

def write_conf(entry_server, exit_server, privkey, address):
    if not exit_server:
        exit_server = {"port" : "51820", "pubkey" : entry_server["pubkey"]}
        config_file = f"m_{entry_server['country.code'].upper()}.{entry_server['city.code']}.conf"
    else:
        config_file = f"m_{entry_server['country.code'].upper()}.{entry_server['city.code']}-{exit_server['country.code'].upper()}.{exit_server['city.code']}.conf"
    with open(config_file, "w") as f:
        f.write(f"[Interface]\n")
        f.write(f"PrivateKey = {privkey}\n")
        f.write(f"Address = {address}\n")
        f.write(f"DNS = 10.64.0.1\n")
        f.write(f"PostUp = \"\"{sys.executable}\" \"{os.path.dirname(os.path.abspath(__file__)) + os.sep}starter.py\" %WIREGUARD_TUNNEL_NAME%\"\n")
        f.write(f"\n")
        f.write(f"[Peer]\n")
        f.write(f"PublicKey = {exit_server['pubkey']}\n")
        f.write(f"Endpoint = {entry_server['ip4']}:{exit_server['port']}\n")
        f.write(f"AllowedIPs = 0.0.0.0/0, ::/0\n")
        f.write(f"PersistentKeepalive = 25")
    return(config_file)

def install_shortcut():
    shortcut = pythoncom.CoCreateInstance(shell.CLSID_ShellLink, None, pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink)
    shortcut.SetPath(os.environ["COMSPEC"])
    shortcut.SetArguments(f"/c \"\"{sys.executable}\" \"{os.path.dirname(os.path.abspath(__file__)) + os.sep}main.py\"\"")
    shortcut.SetWorkingDirectory(os.path.dirname(os.path.abspath(__file__)))
    shortcut.QueryInterface(pythoncom.IID_IPersistFile).Save(os.environ["USERPROFILE"] + os.sep + "Desktop" + os.sep + "Mullvad Controller.lnk", 0)