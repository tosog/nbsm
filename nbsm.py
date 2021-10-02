from Cryptodome.Cipher import AES
import binascii
import serial
import datetime

encKey = bytearray(binascii.unhexlify("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"))

def decrypt_msg(readdata):

    LandisDataSize = 111
    LandisHDCLHeaderSize = 13

    systitle = readdata[LandisHDCLHeaderSize + 1:LandisHDCLHeaderSize + 1 + 8] # 8 bytes
    nonce = readdata[LandisHDCLHeaderSize + 11:LandisHDCLHeaderSize + 11 + 4]  # 4 bytes

    initvec = systitle + nonce

    cipher = AES.new(encKey, AES.MODE_GCM, initvec)
    plaintxt = cipher.decrypt(readdata[LandisHDCLHeaderSize + 15:-3])

    print("\n")

    Year = int.from_bytes(plaintxt[6:8], "big") 
    Month = plaintxt[8]
    Day = plaintxt[9]
    Hour = plaintxt[11]
    Minute = plaintxt[12]
    Second = plaintxt[13]
    print(datetime.datetime(Year, Month, Day, Hour, Minute, Second))

    L1Voltage = int.from_bytes(plaintxt[21:23], "big") 
    L2Voltage = int.from_bytes(plaintxt[24:26], "big") 
    L3Voltage = int.from_bytes(plaintxt[27:29], "big")
    print(L1Voltage,"-",L2Voltage,"-", L3Voltage, "[V]")

    L1Current = int.from_bytes(plaintxt[30:32], "big") / 100
    L2Current = int.from_bytes(plaintxt[33:35], "big") / 100
    L3Current = int.from_bytes(plaintxt[36:38], "big") / 100
    print(L1Current,"-",L2Current,"-", L3Current, "[A]")

    ImportPower = int.from_bytes(plaintxt[39:43], "big")
    ExportPower = int.from_bytes(plaintxt[44:48], "big")
    print(ImportPower,"-", ExportPower, "[W]")

    ImportEnergy = int.from_bytes(plaintxt[49:53], "big")
    ExportEnergy = int.from_bytes(plaintxt[54:58], "big")
    print(ImportEnergy,"-", ExportEnergy, "[Wh]")

def read_from_usb():
    tty = serial.Serial(port='/dev/ttyUSB0', baudrate = 9600, parity =serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, timeout=0)

    data = bytearray()
    while len(data) < 240:
            while tty.in_waiting > 0:
                data += tty.read()
    return data

#main
while True:
    data = read_from_usb()
    if (len(data) == 240): # ignore data if invalid length (e.g. first read after start)
        decrypt_msg(data)
