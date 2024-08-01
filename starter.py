import subprocess
import time
import platform
import sys
import os.path

if platform.system()=="Windows":
	ping_args = ["%SystemRoot%\\System32\\ping.exe", "-n", "1", "10.64.0.1"]
	mvup_args = [os.path.dirname(os.path.abspath(__file__)) + os.sep + "mullvad-upgrade-tunnel.exe", "-wg-interface", "%WIREGUARD_TUNNEL_NAME%"]
elif platform.system()=="Linux":
	ping_args = ["/usr/bin/ping", "-c", "1", "10.64.0.1"]
	mvup_args = [os.path.dirname(os.path.abspath(__file__)) + os.sep + "mullvad-upgrade-tunnel", "-wg-interface", "%i"]
else:
    print("Error : You are not on a supported platform, exiting.")
    sys.exit(1)

while subprocess.run(args).returncode == 1:
	time.sleep(1)

subprocess.run(mvup_args)