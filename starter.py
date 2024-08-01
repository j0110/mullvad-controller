#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import time
import platform
import sys
import os.path

if platform.system()=="Windows":
	ping_args = [os.environ["SYSTEMROOT"] + os.sep + "System32" + os.sep + "ping.exe", "-n", "1", "10.64.0.1"]
	mvup_args = [os.path.dirname(os.path.abspath(__file__)) + os.sep + "mullvad-upgrade-tunnel.exe", "-wg-interface", sys.argv[1]]
elif platform.system()=="Linux":
	ping_args = ["/usr/bin/ping", "-c", "1", "10.64.0.1"]
	mvup_args = [os.path.dirname(os.path.abspath(__file__)) + os.sep + "mullvad-upgrade-tunnel", "-wg-interface", sys.argv[1]]
else:
    print("Error : You are not on a supported platform, exiting.")
    sys.exit(1)

while subprocess.run(ping_args).returncode == 1:
	time.sleep(1)
	print("Waiting while 10.64.0.1 is unavailable...", file = f)
print("10.64.0.1 available !",file = f)
print("", file = f)
print(mvup_args, file = f)
subprocess.run(mvup_args)