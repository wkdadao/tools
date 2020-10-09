import binascii
import sys
import os

bFile = sys.argv[1]

with open(bFile, 'rb') as bf:
    readBytes = bf.read()
    readHex = binascii.b2a_base64(readBytes)
    readStr = readHex.decode()

    tFolder = bFile + '_text'
    if not os.path.exists(tFolder):
        os.makedirs(tFolder)

    start = 0
    fileIndex = 1
    fileSize = 8 * 1024 * 1024
    while start < len(readStr):
        end = min(len(readStr), start + fileSize)
        tFile =  tFolder + '/' + str(fileIndex) + '.txt'
        print('tFile=' + tFile + ', start=' + str(tFile) + ', end=' + str(end))
        with open(tFile, 'w') as tf:
            tf.write(readStr[start:end])
        fileIndex += 1
        start += fileSize
