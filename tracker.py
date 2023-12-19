from metainfo import MetaInfo
from connections.http.http_request import HttpRequest
from connections.udp.udp_connection import UdpConnection
from utils.bencoding import Decoder
import random
import socket

class Tracker:
    def __init__(self, meta_info: MetaInfo):
        '''
        docs for understanding tracker request params
        https://wiki.theory.org/BitTorrentSpecification#Tracker_HTTP.2FHTTPS_Protocol
        '''

        self.meta_info = meta_info
        self.info_hash = self.meta_info.info_hash
        self.peer_id = self.__generate_peer_id()
        self.port = 6881
        self.uploaded = 0
        self.downloaded = 0

        self.peers = []

    def __generate_peer_id(self):
        '''
        docs for logic behind peer_id 
        https://wiki.theory.org/BitTorrentSpecification#peer_id
        '''

        return '-NA0004-' + ''.join(
            str(random.randint(0, 9)) for i in range(12))
    
    def http_request(self):
        '''
        used for HTTP trackers
        '''

        request_param = {'info_hash' : self.info_hash,
                         'peer_id' : self.peer_id,
                         'port' : self.port,
                         'uploaded' : self.uploaded,
                         'downloaded' : self.downloaded,
                         'left' : self.meta_info.length,
                         'compact' : 1,
                         'event' : 'started'
                        }
        
        request = HttpRequest()

        response_content = request.format_request(request_param, self.meta_info.announce_url)
        decoded_response = Decoder(response_content).decode()
        print(decoded_response[b'peers6'].decode('utf8'))
        parsed_info = request.parse_request(decoded_response)

    def udp_request(self):
        '''
        used for UDP trackers - more efficient than HTTP due
        to decreased # of packets and packet size
        '''

        # SOCK_DGRAM is used for UDP connections
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # need IP address and port to send packet
        ip_address = socket.gethostbyname(self.meta_info.announce_url.hostname)
        port = self.meta_info.announce_url.port

        address = (ip_address, port)

        connection = UdpConnection()

        connect_response = connection.connect_request(sock, address)

        # decoded_response = connect_response.decode()

    def get_peers(self):
        scheme = self.meta_info.announce_url.scheme

        if scheme == 'http' or scheme == 'https':
            self.http_request()
        elif scheme == 'udp':
            self.udp_request()
        else:
            raise Exception("Invalid scheme found in announce contents")
        
        return self.peers