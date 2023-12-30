import requests
from collections import OrderedDict
from urllib.parse import urlencode
import ipaddress
from models.peer import Peer

class HttpRequest:
    def format_request(self, request_param: dict, announce: tuple) -> bytes:
        '''
        docs for understanding url formatting
        https://www.rfc-editor.org/rfc/rfc1808.html#section-2.1
        '''
        
        url = announce.scheme + '://' + announce.netloc + announce.path + '?'

        response = requests.get(url, params=request_param)
        
        return response.content
    
    def parse_request(self, response) -> tuple:
        '''
        parse through the response and 
        return all important information

        docs for understanding response
        https://wiki.theory.org/BitTorrentSpecification#Tracker_Response
        '''

        peers = []
        interval = response[b'interval']

        if b'peers' in response and type(response[b'peers']) is bytes:
            peers = self.__compact_peers(response[b'peers'])
        elif b'peers6' in response and type(response[b'peers6']) is bytes:
            peers = self.__ipv6_peers(response[b'peers6'])
        elif b'peers' in response and type(response[b'peers']) is list:
            peers = self.__dict_peers(response[b'peers'])
        else:
            raise TypeError('Not a supported tracker response - cannot be parsed')
        
        return (peers, interval)
        
    def __compact_peers(self, peers: bytes) -> list:
        '''
        fetches the list of peers from compact mode

        when peers is given in compact mode
        - first 4 bytes are IP address
        - next 2 bytes are port number
        '''

        peers_list = []

        for index in range(0, len(peers), 6):
            ip_bytes = peers[index : index + 4]
            port_bytes = peers[index + 4 : index + 6]

            # funcs. utilize big endian by default
            ip_address = str(ipaddress.IPv4Address(ip_bytes))
            port = str(int.from_bytes(port_bytes))

            peers_list.append(Peer(ip_address, port))

        return peers_list
    
    def __ipv6_peers(self, peers: bytes) -> list:
        '''
        fetches the list of peers when given in bytes of IPv6

        - first 16 bytes are IP address
        - next 2 bytes are port number
        '''

        peers_list = []

        for index in range(0, len(peers), 18):
            ip_address = str(ipaddress.IPv6Address(peers[index : index + 16]))
            port = str(int.from_bytes(peers[index + 16 : index + 18]))

            peers_list.append(Peer(ip_address, port))

        return peers_list
    
    def __dict_peers(self, peers: list) -> list:
        '''
        fetches the list of peers when given in a 
        list of OrderedDicts
        '''

        peers_list = []

        for peer in peers:
            ip_address = str(ipaddress.ip_address(peer[b'ip'].decode()))
            port = str(peer[b'port'])

            peers_list.append(Peer(ip_address, port))

        return peers_list