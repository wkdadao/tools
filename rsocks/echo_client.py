import selectors
import socket

sel = selectors.DefaultSelector()

def read(conn, mask):
    data = conn.recv(1000)  # Should be ready
    if data:
        print('echoing', repr(data), 'to', conn)
    else:
        print('closing', conn)
        sel.unregister(conn)
        conn.close()

sock = socket.socket()
sock.connect(('localhost', 1080))
sock.setblocking(False)
sel.register(sock, selectors.EVENT_READ, read)
sock.send(b'rainexus')

while True:
    events = sel.select()
    for key, mask in events:
        callback = key.data
        callback(key.fileobj, mask)