#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import ctypes
import os
import subprocess
import shutil
import glob
import sys
import requests
import zipfile
import io

def is_admin():
    return(ctypes.windll.shell32.IsUserAnAdmin() == 1)

def install_module(module, deb=None):
    subprocess.run([sys.executable, "-m", "pip", "install", module], check=True)

def extra_pip():
    try:
        import winreg
    except ModuleNotFoundError:
        print("Installing winreg...")
        install_module("winreg") 

    try:
        from win32com.shell import shell
        import pythoncom
    except ModuleNotFoundError:
        print("Installing pywin32...")
        install_module("pywin32") 

def write_registry_key():
    import winreg
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
    from win32com.shell import shell
    import pythoncom
    shortcut = pythoncom.CoCreateInstance(shell.CLSID_ShellLink, None, pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink)
    shortcut.SetPath(os.environ["COMSPEC"])
    shortcut.SetArguments(f"/c \"\"{sys.executable}\" \"{os.path.dirname(os.path.abspath(__file__)) + os.sep}main.py\"\"")
    shortcut.SetWorkingDirectory(os.path.dirname(os.path.abspath(__file__)))
    shortcut.QueryInterface(pythoncom.IID_IPersistFile).Save(os.environ["USERPROFILE"] + os.sep + "Desktop" + os.sep + "Mullvad Controller.lnk", 0)

def check_psexec():
    print("Checking if PsExec64 executable is present.")
    for file in glob.glob(os.path.dirname(os.path.abspath(__file__)) + os.sep + "*"):
        if file.split(os.sep)[-1] == "PsExec64.exe":
            print("PsExec64 is present, skipping downloading it.")
            # TODO : check it with .asc file
            return
    print("Downloading PsExec64 using SysInternals servers.")

    response = requests.get("https://download.sysinternals.com/files/PSTools.zip")
    if response.status_code // 100 != 2:
        print("Error: Unable to connect to SysInternals servers.", file=sys.stderr)
        sys.exit(1)
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        with z.open("PsExec64.exe") as f_src, open(os.path.dirname(os.path.abspath(__file__)) + os.sep + "PsExec64.exe", "wb") as f_dest:
            f_dest.write(f_src.read())
