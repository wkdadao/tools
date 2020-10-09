import binascii
import sys

tFile = sys.argv[1]
bFile = tFile + '.bin'

with open(tFile, 'r') as tf:
    readStr = tf.read()    
    readBytes = binascii.a2b_base64(readStr)
    with open(bFile, 'wb') as bf:
        bf.write(readBytes)
