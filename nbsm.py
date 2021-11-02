from Cryptodome.Cipher import AES
import argparse
import binascii
import serial
import datetime
import json
import requests
import time

# CONFIG PART

# the encryption key you've got from Netz Burgenland. This is not the auth_key, which is not needed at all
cfgEncKey = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

# if the publish mode is json, configure the http(s) endpoint here
cfgJsonEndpoint = "http://kodal:8080/goSmartPV/SMCollect" 

# if the publish mode is mqtt, configure the mqtt variables here
cfgMqttServer = "192.168.1.235"
cfgMqttUser = "" # leave empty if no user/password is needed
cfgMqttPassword = "" # leave empty if no user/password is needed
cfgMqttMainTopic = "nbsm/1/"

# END CONFIG PART

# parse command line parameeters to see which libraries are needed
parser = argparse.ArgumentParser()
parser.add_argument("--mode", help="The publish mode", choices=["stdout","json", "mqtt"], required=True)
args = parser.parse_args()
if (args.mode == "json"):
    import requests
elif (args.mode == "mqtt"):
    import paho.mqtt.client as mqtt

encKey = bytearray(binascii.unhexlify(cfgEncKey))

def decrypt_msg(readdata):

    LandisDataSize = 111
    LandisHDCLHeaderSize = 13
    
    systitle = readdata[LandisHDCLHeaderSize + 1:LandisHDCLHeaderSize + 1 + 8] # 8 bytes
    nonce = readdata[LandisHDCLHeaderSize + 11:LandisHDCLHeaderSize + 11 + 4]  # 4 bytes

    initvec = systitle + nonce

    cipher = AES.new(encKey, AES.MODE_GCM, initvec)
    plaintxt = cipher.decrypt(readdata[LandisHDCLHeaderSize + 15:-3])

    Year = int.from_bytes(plaintxt[6:8], "big") 
    Month = plaintxt[8]
    Day = plaintxt[9]
    Hour = plaintxt[11]
    Minute = plaintxt[12]
    Second = plaintxt[13]

    L1Voltage = int.from_bytes(plaintxt[21:23], "big") 
    L2Voltage = int.from_bytes(plaintxt[24:26], "big") 
    L3Voltage = int.from_bytes(plaintxt[27:29], "big")

    L1Current = int.from_bytes(plaintxt[30:32], "big") / 100
    L2Current = int.from_bytes(plaintxt[33:35], "big") / 100
    L3Current = int.from_bytes(plaintxt[36:38], "big") / 100

    ImportPower = int.from_bytes(plaintxt[39:43], "big")
    ExportPower = int.from_bytes(plaintxt[44:48], "big")

    ImportEnergy = int.from_bytes(plaintxt[49:53], "big")
    ExportEnergy = int.from_bytes(plaintxt[54:58], "big")

    jsdata = {}
    jsdata["datetime"] = datetime.datetime(Year, Month, Day, Hour, Minute, Second).isoformat()

    jsdata["L1"] = {}
    jsdata["L1"]["v"] = L1Voltage
    jsdata["L1"]["a"] = L1Current
    
    jsdata["L2"] = {}
    jsdata["L2"]["v"] = L2Voltage
    jsdata["L2"]["a"] = L2Current

    jsdata["L3"] = {}
    jsdata["L3"]["v"] = L3Voltage
    jsdata["L3"]["a"] = L3Current

    jsdata["actual"] = {}
    jsdata["actual"]["in"] = ImportPower
    jsdata["actual"]["out"] = ExportPower

    jsdata["total"] = {}
    jsdata["total"]["in"] = ImportEnergy
    jsdata["total"]["out"] = ExportEnergy

    if (args.mode == "stdout"):
        print(json.dumps(jsdata))
    elif (args.mode == "json"):
        #requests.post('http://kodal:8080/goSmartPV/SMCollect', json=json.dumps(jsdata))
        requests.post(cfgJsonEndpoint, json=jsdata)
    elif (args.mode == "mqtt"):
        publish_mqtt(jsdata)

def publish_mqtt(jsdata):
    client = mqtt.Client("nbsm")

    if (len(cfgMqttUser) > 0):
        client.username_pw_set(username=cfgMqttUser, password=cfgMqttPassword)

    client.connect(cfgMqttServer)

    client.publish(cfgMqttMainTopic + "status/datetime", jsdata["datetime"])
    client.publish(cfgMqttMainTopic + "status/L1/v", jsdata["L1"]["v"])
    client.publish(cfgMqttMainTopic + "status/L1/a", jsdata["L1"]["a"])
    client.publish(cfgMqttMainTopic + "status/L2/v", jsdata["L2"]["v"])
    client.publish(cfgMqttMainTopic + "status/L2/a", jsdata["L2"]["a"])
    client.publish(cfgMqttMainTopic + "status/L3/v", jsdata["L3"]["v"])
    client.publish(cfgMqttMainTopic + "status/L3/a", jsdata["L3"]["a"])
    client.publish(cfgMqttMainTopic + "status/actual/in", jsdata["actual"]["in"])
    client.publish(cfgMqttMainTopic + "status/actual/out", jsdata["actual"]["out"])
    client.publish(cfgMqttMainTopic + "status/total/in", jsdata["total"]["in"])
    client.publish(cfgMqttMainTopic + "status/total/out", jsdata["total"]["out"])

### main ###
tty = serial.Serial(port='/dev/ttyUSB0', baudrate = 9600, parity =serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, timeout=1)

data = bytearray()

while True:
    while tty.in_waiting > 0:
        readidx = len(data)
        b = tty.read()
        data += b
        #print(b.hex(), end='', flush=True)
        #print(" ", readidx)

        startpos = data.find(b'\x7e\xa0')

        if (startpos >= 0):
            # found start position. calc corrected idx within the message
            idx = readidx - startpos
            if (idx == 2):
                totallen = data[readidx]
                data += tty.read(totallen - 1) #-1: length is already included
                #print("process: ", data[startpos:].hex())
                decrypt_msg(data[startpos:])
                data = bytearray()

    time.sleep(0.1)

