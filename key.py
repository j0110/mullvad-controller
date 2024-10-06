#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import hashlib
import base64
import socket
import getpass

def key_to_bytes(account, privkey, address):
	key_bytes = b""
	key_bytes += int(account).to_bytes(8, byteorder="big")
	key_bytes += base64.b64decode(privkey)
	address = [a.split("/")[0] for a in address.split(",")]
	key_bytes += socket.inet_pton(socket.AF_INET, address[0])
	key_bytes += socket.inet_pton(socket.AF_INET6, address[1])
	return(key_bytes + 4*b'\x00')

def bytes_to_key(key_bytes):
	account = str(int.from_bytes(key_bytes[0:8], byteorder="big"))
	privkey = base64.b64encode(key_bytes[8:40]).decode()
	ip4 = socket.inet_ntop(socket.AF_INET, key_bytes[40:44])
	ip6 = socket.inet_ntop(socket.AF_INET6, key_bytes[44:60])
	address = ip4 + "/32," + ip6 + "/128"
	return(account, privkey, address)

def xor_bytes(bytes_1, bytes_2):
	int_1 = int.from_bytes(bytes_1, byteorder="big")
	int_2 = int.from_bytes(bytes_2, byteorder="big")
	return((int_1 ^ int_2).to_bytes(64, byteorder="big"))

def read_and_decrypt(password):
	with open(os.path.dirname(os.path.abspath(__file__)) + os.sep + "key", "rb") as key_file:
		content = key_file.read()
		salt = content[0:16]
		crypted_bytes = content[16:80]
		key = hashlib.pbkdf2_hmac("sha512", password.encode("utf-8"), salt, 10**6)
		return(xor_bytes(key, crypted_bytes))

def crypt_and_write(password, key_bytes):
	salt = os.urandom(16)
	key = hashlib.pbkdf2_hmac("sha512", password.encode("utf-8"), salt, 10**6)
	crypted_bytes = xor_bytes(key, key_bytes)
	with open(os.path.dirname(os.path.abspath(__file__)) + os.sep + "key", "wb") as key_file:
		key_file.write(salt + crypted_bytes)

def load_key():
	password = getpass.getpass("Please enter the password you previously used for mullvad-controller :\n> ")
	key_bytes = read_and_decrypt(password)
	return(bytes_to_key(key_bytes))

def write_key(account, privkey, address):
	password = getpass.getpass("Please provide a new password for securing your private key :\n> ")
	key_bytes = key_to_bytes(account, privkey, address)
	crypt_and_write(password, key_bytes)