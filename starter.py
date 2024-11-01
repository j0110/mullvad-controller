#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import time
import platform
import sys
import os.path

if platform.system()=="Windows":
	ping_args = [os.environ["SYSTEMROOT"] + os.sep + "System32" + os.sep + "ping.exe", "-n", "1", "10.64.0.1"]
	mvup_args = [os.path.dirname(os.path.abspath(__file__)) + os.sep + "PsExec64.exe", "-i", "-s", "-accepteula", "-nobanner", os.path.dirname(os.path.abspath(__file__)) + os.sep + "mullvad-upgrade-tunnel.exe", "-wg-interface", sys.argv[1]]
elif platform.system()=="Linux":
	ping_args = ["/usr/bin/ping", "-c", "1", "10.64.0.1"]
	mvup_args = [os.path.dirname(os.path.abspath(__file__)) + os.sep + "mullvad-upgrade-tunnel", "-wg-interface", sys.argv[1]]
else:
    print("Error : You are not on a supported platform, exiting.")
    sys.exit(1)

print("Checking if 10.64.0.1 is available...")
while subprocess.run(ping_args).returncode != 0:
	print("It failed, waiting 1 second...")
	time.sleep(1)
	print("Checking again if 10.64.0.1 is available...")
print("10.64.0.1 available !")

print("Executing mullvad-upgrade-tunnel...")
while subprocess.run(mvup_args).returncode != 0:
	print("It failed, waiting 1 second...")
	time.sleep(1)
	print("Executing again mullvad-upgrade-tunnel...")
print("Executed successfully mullvad-upgrade-tunnel !")