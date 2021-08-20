
import selectors
import socket
import threading
import json
from logger import make_logger
from enum import Enum

class DstInfo(object):
    def __init__(self, connectionId) -> None:
        super().__init__()
        self.connectionId = connectionId
        self.buf = bytes()

class RemoteServer(object):
    def __init__(self, host, port, logger, backlog=128) -> None:
        super().__init__()
        self.host = host
        self.port = port
        self.logger = logger
        self.backlog = backlog
        self.sel = selectors.DefaultSelector()
        self.selLock = threading.Lock()
        self.sock = socket.socket()
        self.sock.bind((self.host, self.port))
        self.sock.listen(self.backlog)
        self.sock.setblocking(False)
        self.sel.register(self.sock, selectors.EVENT_READ, self.accept)

        self.clientBuf = bytes()
        self.clientProcessGen = self.clientProcessGenerator()

        self.dstInfos = dict()
        self.id2DstSock = dict()

    def selRegisterWithLock(self, sock, event, callback):
        with self.selLock:
            self.sel.register(sock, event, callback)

    def selUnregisterWithLock(self, sock):
        with self.selLock:
            self.sel.unregister(sock)

    def accept(self, sock, mask) -> None:
        clientSock, addr = sock.accept()  # Should be ready
        self.logger.info('accepted' + str(clientSock) + ' from ' + str(addr))
        clientSock.setblocking(False)
        self.selRegisterWithLock(clientSock, selectors.EVENT_READ, self.readClient)

    def connectDstThread(self, dstSock, connectInfo):
        dstSock.connect((connectInfo['h'], int(connectInfo['p'])))
        dstSock.setblocking(False)
        self.selRegisterWithLock(dstSock, selectors.EVENT_WRITE | selectors.EVENT_READ, self.hanldeDst)

    def clientProcessGenerator(self):
        while True:
            #bufLen
            while len(self.clientBuf) < 1:
                yield 'wait for bufLen'
            bufLenByte = self.clientBuf[0:1]
            self.clientBuf = self.clientBuf[1:]
            bufLen = int.from_bytes(bufLenByte, byteorder='big')

            #flag
            while len(self.clientBuf) < 3:
                yield 'wait for flag'
            flagBytes = self.clientBuf[0:3]
            self.clientBuf = self.clientBuf[3:]
            flag = int.from_bytes(flagBytes, byteorder='big')
            isConnect = True if (flag & 2 ** 23) > 0 else False
            connectionId = flag & (2 ** 23 - 1)

            #buf
            while len(self.clientBuf) < bufLen:
                yield 'wait for buf'
            buf = self.clientBuf[0:bufLen]
            self.clientBuf = self.clientBuf[bufLen:]

            if isConnect:
                connectInfo = json.loads(buf.decode())
                self.logger.info('connected to remote: connectionId=' + str(connectionId) + ', isConnect=' + str(isConnect) + ', bufLen=' + str(bufLen) + ', connectInfo=' + str(connectInfo))
                dstSock = socket.socket()
                self.id2DstSock[connectionId] = dstSock
                self.dstInfos[dstSock] = DstInfo(connectionId)
                t = threading.Thread(target=self.connectDstThread, args=(dstSock, connectInfo))
                t.daemon = True
                t.start()
            else:
                dstSock = self.id2DstSock[connectionId]
                dstInfo = self.dstInfos[dstSock]
                dstInfo.buf += buf
                self.logger.info('arrived to remote: connectionId=' + str(connectionId) + ', isConnect=' + str(isConnect) + ', bufLen=' + str(bufLen))

    def sendToClient(self, dstSock, connectionId, buf):
        bufLen = min(256, len(buf))
        bufLenByte = bufLen.to_bytes(1, byteorder='big')
        sendBuf = buf[0:bufLen]
        buf = buf[bufLen:]
        connectionIdBytes = connectionId.to_bytes(3, byteorder='big')
        dstSock.sendall(bufLenByte + connectionIdBytes + sendBuf)
        self.logger.info('sent to client: connectionId=' + str(self.connectionId) + ', bufLen=' + str(bufLen))

        if buf:
           self.sendToClient(dstSock, connectionId, buf)

    def readClient(self, clientSock, mask) -> None:
        #$try:
        buf = clientSock.recv(self.backlog)
        if buf:
            self.clientBuf += buf
            next(self.clientProcessGen)
        #except Exception as e:
            #self.logger.info('readClient Exception: ' + str(e))
            #self.closeSock(clientSock)

    def hanldeDst(self, dstSock, mask) -> None:
        if mask & selectors.EVENT_WRITE:
            self.writeDst(dstSock)
        elif mask & selectors.EVENT_READ:
            self.readDst(dstSock)

    def readDst(self, dstSock) -> None:
        try:
            buf = dstSock.recv(self.backlog)
            if buf:
                dstInfo = self.dstInfos[dstSock]
                self.sendToClient(self, dstSock, dstInfo.connectionId, buf)
        except Exception as e:
            self.logger.info('readDst Exception: ' + str(e))
            self.closeSock(dstSock)

    def writeDst(self, dstSock) -> None:
        try:
            dstInfo = self.dstInfos[dstSock]
            if dstInfo.buf:
                dstSock.sendAll(dstInfo.buf)
                dstInfo.buf = bytes()
        except Exception as e:
            self.logger.info('writeDst Exception: ' + str(e))
            self.closeSock(dstSock)

    def closeSock(self, sock) -> None:
        self.logger.info('closing ' + str(sock))
        self.selUnregisterWithLock(sock)
        sock.close()

    def run(self) -> None:
        while True:
            events = self.sel.select()
            for key, mask in events:
                callback = key.data
                callback(key.fileobj, mask)

logger = make_logger(None)
ls = RemoteServer('localhost', 1081, logger)
ls.run()