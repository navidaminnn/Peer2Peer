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

    def __generate_transaction_id(self) -> int:
        '''
        transaction_id should be in 
        range of all non-negative numbers
        '''

        return random.randint(0, 2**31 - 1)

    def create_packet_conn(self) -> bytes:
        '''
        docs for understanding pack func.
        https://docs.python.org/3/library/struct.html

        - protocol_id is 8 bytes
        - action is 4 bytes
        - transaction_id is 4 bytes
        '''

        # should all be unsigned
        return struct.pack('>QII', self.protocol_id, self.action, self.transaction_id)
    
    def create_packet_ann(self, param: dict):
        '''
        docs for announce req
        https://www.bittorrent.org/beps/bep_0015.html
        '''

        return struct.pack('>QII20B20BQQQIIIiH',
                           param['connection_id'],
                           1, # action
                           param['transaction_id'],
                           param['info_hash'],
                           param['peer_id'],
                           param['downloaded'],
                           param['left'],
                           param['uploaded'],
                           0, # event
                           0, # ip address - default
                           0, # key
                           -1, # num_want
                           param['port'])

    def send_request(self, sock: socket.socket, address: tuple, packet: bytes) -> bytes:
        sock.sendto(packet, address)

        while True:
            try:
                #TODO: add some error checking to ensure we received 
                # a valid packet?

                # buffer of 2048 bytes
                response = sock.recv(2048)
                return response 
            except TimeoutError:
                #TODO: what should happen if there's a timeout?
                # could maybe run the func. again?
                raise TimeoutError("Socket response wasn't completed in time")

    def parse_connection(self, response: bytes) -> dict:
        '''
        - action is 4 bytes
        - transaction_id is 4 bytes
        - connection_id is 8 bytes (what we care about!)
        '''

        action, transaction_id, connection_id = struct.unpack('>IIQ', response)

        # ensure transaction_id matches up
        if transaction_id != self.transaction_id:
            raise Exception('Transaction IDs don\'t match up')
        
        # ensure action remains consistent
        if action != 0:
            raise Exception('Inconsistent action - connection didn\'t process correctly')

        resp_dict = {
            'action' : action,
            'transaction_id' : transaction_id,
            'connection_id' : connection_id
        }

        return resp_dict
    
    def parse_announce(self, response: bytes):
        '''
        CURRENTLY ONLY SUPPORTS IPv4 - CONSIDER ADDING
        IPv6 COMPATIBILITY

        - action is 4 bytes
        - transaction_id is 4 bytes
        - interval is 4 bytes
        - leechers is 4 bytes
        - seeders is 4 bytes
        - IP address is 4 bytes (n times for each peer)
        - TCP port is 2 bytes (n times for each peer)
        '''

        

        pass