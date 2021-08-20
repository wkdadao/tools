
import selectors
import socket
import json
from logger import make_logger

class ClientConnection(object):
    VER = b'\x05'
    METHOD = b'\x00'
    SUCCESS = b'\x00'
    SOCK_FAIL = b'\x01'
    NETWORK_FAIL = b'\x02'
    HOST_FAIL = b'\x04'
    REFUSED = b'\x05'
    TTL_EXPIRED = b'\x06'
    UNSUPPORTED_CMD = b'\x07'
    ADDR_TYPE_UNSUPPORT = b'\x08'
    UNASSIGNED = b'\x09'

    ADDR_TYPE_IPV4 = b'\x01'
    ADDR_TYPE_DOMAIN = b'\x03'
    ADDR_TYPE_IPV6 = b'\x04'

    CMD_TYPE_CONNECT = b'\x01'
    CMD_TYPE_TCP_BIND = b'\x02'
    CMD_TYPE_UDP = b'\x03'

    def __init__(self, clientSock, lhost, lport, remoteSock, connectionId, logger) -> None:
        super().__init__()
        self.clientSock = clientSock
        self.lhost = lhost
        self.lport = lport
        self.remoteSock = remoteSock
        self.connectionId = connectionId
        self.logger = logger
        self.buf = bytes()
        self.dest_host = None
        self.dest_port = None
        self.established = False
        self.establishingGen = self.establishingGenerator()

    def establishingGenerator(self):
        # ver, nmethods, methods
        while len(self.buf) < 3:
            yield 'wait for ver, nmethods, methods'
        self.buf = self.buf[3:]
        self.clientSock.sendall(self.VER + self.METHOD)

        # ver, cmd, rsv, address_type
        while len(self.buf) < 4:
            yield 'wait for ver, cmd, rsv, address_type'
        cmd = self.buf[1:2]
        address_type = self.buf[3:4]
        self.buf = self.buf[4:]
        self.clientSock.sendall(self.VER + self.METHOD)

        dst_addr = None
        dst_port = None
        if address_type == self.ADDR_TYPE_IPV4:
            # dst_addr, dst_port
            while len(self.buf) < 6:
                yield 'wait for dst_addr, dst_port'
            dst_addr = self.buf[0:4]
            dst_port = self.buf[4:6]
            self.buf = self.buf[8:]
            dst_addr = '.'.join([str(i) for i in dst_addr])
        elif address_type == self.ADDR_TYPE_DOMAIN:
            # addr_len
            while len(self.buf) < 1:
                yield 'wait for addr_len'
            addr_len = ord(self.buf[0:1])
            self.buf = self.buf[1:]

            # dst_addr, dst_port
            while len(self.buf) < addr_len + 2:
                yield 'wait for dst_addr, dst_port'
            dst_addr = self.buf[0:addr_len]
            dst_port = self.buf[addr_len:addr_len+2]
            dst_addr = ''.join([chr(i) for i in dst_addr])
        elif address_type == self.ADDR_TYPE_IPV6:
            # dst_addr, dst_port
            while len(self.buf) < 18:
                yield 'wait for dst_addr, dst_port'
            dst_addr = self.buf[0:16]
            dst_port = self.buf[16:18]
            self.buf = self.buf[18:]
            tmp_addr = []
            for i in range(len(dst_addr) // 2):
                tmp_addr.append(chr(dst_addr[2 * i] * 256 + dst_addr[2 * i + 1]))
            dst_addr = ':'.join(tmp_addr)

        dst_port = dst_port[0] * 256 + dst_port[1]

        serverIp = ''.join([chr(int(i)) for i in socket.gethostbyname(self.lhost).split('.')])
        severInfo = serverIp + chr(self.lport // 256) + chr(self.lport % 256)

        if cmd == self.CMD_TYPE_TCP_BIND:
            self.logger.error('TCP Bind requested, but is not supported by socks5_server')
            self.clientSock.close()
        elif cmd == self.CMD_TYPE_UDP:
            self.logger.error('UDP requested, but is not supported by socks5_server')
            self.clientSock.close()
        elif cmd == self.CMD_TYPE_CONNECT:
            self.clientSock.sendall(self.VER + self.SUCCESS + b'\x00' + b'\x01' + severInfo.encode())
            self.dest_host, self.dest_port = dst_addr, dst_port
        else:
            # Unsupport/unknown Command
            self.logger.error('Unsupported/unknown SOCKS5 command requested')
            self.clientSock.sendall(self.VER + self.UNSUPPORTED_CMD + severInfo.encode())
            self.clientSock.close()

    def process(self, buf):
        self.buf += buf

        if not self.established:
            try:
                next(self.establishingGen)
            except StopIteration:
                self.established = True
                self.logger.info('established: dest_host=' + str(self.dest_host) + ', dest_port=' + str(self.dest_port))
                self.connectToRemote()

        if self.buf:
            self.sendToRemote(False, self.buf)
            self.buf = bytes()

    def connectToRemote(self):
        connectInfo = { 'h':self.dest_host, 'p':self.dest_port }
        connectInfoBytes = json.dumps(connectInfo).encode()
        self.sendToRemote(True, connectInfoBytes)

    def sendToRemote(self, isConnect, buf):
        bufLen = min(255, len(buf))
        bufLenByte = bufLen.to_bytes(1, byteorder='big')
        sendBuf = buf[0:bufLen]
        buf = buf[bufLen:]
        flag = self.connectionId
        flag |= 2 ** 23 if isConnect else 0
        flagBytes = flag.to_bytes(3, byteorder='big')
        self.remoteSock.sendall(bufLenByte + flagBytes + sendBuf)
        self.logger.info('sent to remote: connectionId=' + str(self.connectionId) + ', isConnect=' + str(isConnect) + ', bufLen=' + str(bufLen))

        if buf:
           self.sendToRemote(isConnect, buf)

class LocalServer(object):
    def __init__(self, lhost, lport, rhost, rport, logger, backlog=128) -> None:
        super().__init__()
        self.lhost = lhost
        self.lport = lport
        self.rhost = rhost
        self.rport = rport
        self.logger = logger
        self.backlog = backlog
        self.sel = selectors.DefaultSelector()

        self.remoteBuf = bytes()
        self.remoteProcessGen = self.remoteProcessGenerator()
        self.remoteSock = socket.socket()
        self.remoteSock.connect((rhost, rport))
        self.remoteSock.setblocking(False)
        self.sel.register(self.remoteSock, selectors.EVENT_READ, self.readRemote)

        self.sock = socket.socket()
        self.sock.bind((self.lhost, self.lport))
        self.sock.listen(self.backlog)
        self.sock.setblocking(False)
        self.sel.register(self.sock, selectors.EVENT_READ, self.accept)
        self.clientSocks = dict()
        self.connectionIds = dict()
        self.connectionId = 0

    def accept(self, sock, mask) -> None:
        clientSock, addr = sock.accept()  # Should be ready
        self.logger.info('accepted' + str(clientSock) + ' from ' + str(addr))
        clientSock.setblocking(False)
        self.sel.register(clientSock, selectors.EVENT_READ, self.readClient)

        self.connectionId += 1
        clientConnection = ClientConnection(clientSock, self.lhost, self.lport, self.remoteSock, self.connectionId, self.logger)
        self.clientSocks[clientSock] = clientConnection
        self.connectionIds[self.connectionId] = clientConnection

    def remoteProcessGenerator(self):
        while True:
            #bufLen
            while len(self.remoteBuf) < 1:
                yield 'wait for bufLen'
            bufLenByte = self.remoteBuf[0:1]
            self.remoteBuf = self.remoteBuf[1:]
            bufLen = int.from_bytes(bufLenByte, byteorder='big')

            #connectionId
            while len(self.remoteBuf) < 3:
                yield 'wait for connectionId'
            connectionIdBytes = self.remoteBuf[0:3]
            self.remoteBuf = self.remoteBuf[3:]
            connectionId = int.from_bytes(connectionIdBytes, byteorder='big')

            #buf
            while len(self.remoteBuf) < bufLen:
                yield 'wait for buf'
            buf = self.remoteBuf[0:bufLen]
            self.remoteBuf = self.remoteBuf[bufLen:]

            clientConnection = self.connectionIds[connectionId]
            clientConnection.clientSock.sendAll(buf)

    def readRemote(self, remoteSock, mask):
        try:
            buf = remoteSock.recv(self.backlog)
            if buf:
                self.remoteBuf += buf
                next(self.remoteProcessGen)
        except Exception as e:
            self.logger.error('readRemote Exception: ' + str(e))
            exit(-1)

    def readClient(self, clientSock, mask) -> None:
        #try:
        buf = clientSock.recv(self.backlog)
        if buf:
            self.clientSocks[clientSock].process(buf)
        #except Exception as e:
            #self.logger.error('readClient Exception: ' + str(e))
            #self.closeCient(clientSock)

    def closeCient(self, clientSock) -> None:
        self.logger.info('closing ' + str(clientSock))

        if clientSock in self.clientSocks:
            self.connectionIds.pop(self.clientSocks[clientSock].connectionId)
            self.clientSocks.pop(clientSock)

        self.sel.unregister(clientSock)
        clientSock.close()

    def run(self) -> None:
        while True:
            events = self.sel.select()
            for key, mask in events:
                callback = key.data
                callback(key.fileobj, mask)

logger = make_logger(None)
ls = LocalServer('localhost', 1080, 'localhost', 1081, logger)
ls.run()