# -*- coding: utf-8 -*-
""" socks5_server

Supports both python 2 and 3.
"""

__author__ = "Caleb Madrigal"
__date__ = '2016-10-17'

import sys
import argparse
import logging
import socket
import select
import threading

PY3 = sys.version_info[0] == 3
if PY3:
    chr_to_int = lambda x: x
    encode_str = lambda x: x.encode()
else:
    chr_to_int = ord
    encode_str = lambda x: x

SOCK_TIMEOUT = 5  # seconds
RESEND_TIMEOUT = 60  # seconds
MAX_RECEIVE_SIZE = 65536

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


def make_logger(log_path=None, log_level_str='INFO'):
    formatter = logging.Formatter('%(asctime)s: %(name)s (%(levelname)s): %(message)s')
    if log_path:
        log_handler = logging.FileHandler(log_path)
    else:
        log_handler = logging.StreamHandler(sys.stdout)
    log_handler.setFormatter(formatter)
    logger = logging.getLogger('socks5_server')
    logger.addHandler(log_handler)
    log_level = logging.getLevelName(log_level_str.upper())
    logger.setLevel(log_level)
    return logger


class Socks5Server:
    def __init__(self, host, port, logger, backlog=128):
        self.host = host
        self.port = port
        self.logger = logger
        self.backlog = backlog
        self.local_dest_lock = threading.Lock()
        self.dest_local_connection_id = {}
        self.local_connection_id_dest = {}

    def buffer_receive(self, sock):
        """ Reads into the buffer for the corresponding relay socket. """
        buf = sock.recv(MAX_RECEIVE_SIZE)
        if len(buf) == 0:
            self.flush_and_close_sock_pair(sock)
        else:
            target_sock = self.client_dest_map[sock]
            target_sock.send(buf)

    def flush_and_close_sock_pair(self, sock, error_msg=None):
        """ Flush any remaining send buffers to the correct socket, close the sockets, and remove
        the pair of sockets from both the client_dest_map and the sock_send_buffers dicts. """
        if error_msg:
            self.logger.error('flushing and closing pair due to error: %s' % error_msg)
        else:
            self.logger.info('Flushing and closing finished connection pair')
        with self.local_dest_lock:
            connection_id_dest = self.local_connection_id_dest.pop(sock)
            for dest in connection_id_dest.values():
                self.dest_local_connection_id.pop(dest)

    def accept_connection(self):
        (_, addr) = self.server_sock.accept()
        self.logger.info('Connection from: %s:%d' % addr)

    def serve_forever(self):
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.bind((self.host, self.port))
        self.server_sock.listen(self.backlog)
        self.logger.info('Serving on %s:%d' % (self.host, self.port))

        while True:
            connected_sockets = None
            with self.local_dest_lock:
                connected_sockets = list(self.dest_local_connection_id.keys()) + list(self.local_connection_id_dest.keys())
            in_socks = [self.server_sock] + connected_sockets
            in_ready, _, err_ready = select.select(in_socks, [], [], 0.1)

            for sock in in_ready:
                if sock == self.server_sock:
                    self.accept_connection()
                else:
                    try:
                        self.buffer_receive(sock)
                    except Exception as e:
                        self.flush_and_close_sock_pair(sock, str(e))

            for sock in err_ready:
                if sock == self.server_sock:
                    self.logger.critical('Error in server socket; closing down')
                    for c in connected_sockets:
                        c.close()
                    self.server_sock.close()
                    sys.exit(1)
                else:
                    self.flush_and_close_sock_pair(sock, 'Unknown socket error')


def main(args):
    logger = make_logger(log_path=args.log_path, log_level_str=args.log_level)
    socks5_server = Socks5Server(args.host, args.port, logger)
    socks5_server.serve_forever()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--host', action='store', default='',
                        help='IP/Hostname to serve on', type=str)
    parser.add_argument('-p', '--port', action='store', default=1080,
                        help='Port to serve on', type=int)
    parser.add_argument('--log-path', action='store', default=None,
                        help='DEBUG, INFO, WARNING, ERROR, or CRITICAL', type=str)
    parser.add_argument('--log-level', action='store', default='INFO',
                        help='Log file path', type=str)
    args = parser.parse_args()

    main(args)
