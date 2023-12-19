# TODO:
# 1. form a connection to tracker to obtain connection_id
# 2. then, announce request can be made
# docs: https://www.bittorrent.org/beps/bep_0015.html

import socket
import struct
import random

class UdpConnection:
    def __init__(self):
        self.protocol_id = 0x41727101980
        self.action = 0
        self.transaction_id = self.__generate_transaction_id()
        self.packet = self.__create_packet()

    def __generate_transaction_id(self):
        '''
        transaction_id should be in 
        range of all non-negative numbers
        '''

        return random.randint(0, 2**31 - 1)

    def __create_packet(self):
        '''
        docs for understanding pack func.
        https://docs.python.org/3/library/struct.html

        - protocol_id is 8 bytes
        - action is 4 bytes
        - transaction_id is 4 bytes
        '''

        return struct.pack('>qii', self.protocol_id, self.action, self.transaction_id)

    def connect_request(self, sock: socket.socket, address: tuple):
        sock.sendto(self.packet, address)

        while True:
            try:
                #TODO: add some error checking to ensure we received 
                # a valid packet?

                # buffer of 2048 bytes
                response = sock.recv(2048)
                return response
            except socket.timeout:
                #TODO: what should happen if there's a timeout?
                # could maybe run the func. again?
                pass
