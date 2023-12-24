import socket
import struct
import random
import ipaddress
import time
from utils.peer import Peer

class UdpRequest:
    def __init__(self):
        self.protocol_id = 0x41727101980
        self.action = 0
        self.transaction_id = self.__generate_random_val()
        self.attempts = 0

    def __generate_random_val(self) -> int:
        '''
        generate a random non-negative val
        that is within 4 byte range
        '''

        return random.randint(0, 2**31 - 1)
    
    def send_request(self, sock: socket.socket, address: tuple, packet: bytes) -> bytes:
        '''
        docs for understanding buffer
        https://docs.python.org/3/library/socket.html#socket.recv
        '''

        sock.sendto(packet, address)

        while True:
            try:
                # buffer of 2048 bytes
                response = sock.recv(2048)
                break
            except TimeoutError:
                # if there's no response after 5 attempts, raise exception
                self.attempts += 1

                if self.attempts >= 5:
                    raise TimeoutError("Socket response wasn't completed in time")

                # seems to be inconsistent with response time, keep trying
                time.sleep(random.uniform(0.5, 2))
                response = self.send_request(sock, address, packet)
                break

        # response should not be empty
        if not len(response) > 0:
            raise Exception('Response should be 16 bytes (plus buffer)')
        
        return response


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

        return {
            'action' : action,
            'transaction_id' : transaction_id,
            'connection_id' : connection_id
        }

    def create_packet_ann(self, param: dict) -> bytes:
        '''
        docs for announce req
        https://www.bittorrent.org/beps/bep_0015.html
        '''

        # should have total of 98 bytes
        return struct.pack('>QII20s20sQQQIIIiH',
                           *[
                           param['connection_id'], # (8 bytes)
                           param['action'], # defaulted to 1 (4 bytes)
                           param['transaction_id'], # (4 bytes)
                           param['info_hash'], # (20 bytes)
                           param['peer_id'], # (20 bytes)
                           param['downloaded'], # (8 bytes)
                           param['left'], # (8 bytes)
                           param['uploaded'], # (8 bytes)
                           param['event'], # (4 bytes)
                           param['IP address'], # defaulted to 0 (4 bytes)
                           self.__generate_random_val(), # key (4 bytes)
                           param['num_want'], # defaulted to -1 (4 bytes)
                           param['port']]) # (2 bytes)
    
    def parse_announce(self, response: bytes):
        '''
        TODO: currently only supports IPv4 due to 
        gethostbyname() func. returning IPv4 only,
        look into how to implement IPv6

        docs regarding IPv6 (might not need to be implemented?)
        https://www.bittorrent.org/beps/bep_0015.html

        - action is 4 bytes
        - transaction_id is 4 bytes
        - interval is 4 bytes
        - leechers is 4 bytes
        - seeders is 4 bytes
        - IP address is 4 bytes (n times for each peer)
        - TCP port is 2 bytes (n times for each peer)
        '''

        action, transaction_id, interval, leechers, seeders = struct.unpack('>IIIII', response[:20])

        # ensure action remains consistent
        if action != 1:
            raise Exception('Inconsistent action - announcement didn\'t process correctly')
        
        peers_list = []

        for index in range(20, len(response), 6):
            ip_bytes = response[index : index + 4]
            port_bytes = response[index + 4 : index + 6]

            ip_address = str(ipaddress.IPv4Address(ip_bytes))
            port = str(int.from_bytes(port_bytes))

            peers_list.append(Peer(ip_address, port))

        # TODO: do we care about/need any of this aside from interval and peers?
        return {
            'action' : action,
            'transaction_id' : transaction_id,
            'interval' : interval,
            'leechers' : leechers,
            'seeders' : seeders,
            'peers' : peers_list
        }