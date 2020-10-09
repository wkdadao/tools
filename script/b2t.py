import binascii
import sys

bFile = sys.argv[1]
tFile = bFile + '.txt'

with open(bFile, 'rb') as bf:
    readBytes = bf.read()
    readHex = binascii.b2a_base64(readBytes)
    readStr = readHex.decode()
    with open(tFile, 'w') as tf:
        tf.write(readStr)
