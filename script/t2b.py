import binascii
import sys
import os

tFolder = sys.argv[1]
bFile = tFolder + '.bin'

allReadStr = ''
fileIndex = 1
while True:
    tFile = tFolder + '/' + str(fileIndex) + '.txt'
    if not os.path.exists(tFile):
        break
    print(tFile)
    with open(tFile, 'r') as tf:
        readStr = tf.read()
        allReadStr += readStr
    fileIndex += 1
        
readBytes = binascii.a2b_base64(allReadStr)
with open(bFile, 'wb') as bf:
    bf.write(readBytes)
