from metainfo import MetaInfo
from connections.http_request import HttpRequest
from connections.udp_request import UdpRequest
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
        self.interval = None

    def __generate_peer_id(self) -> bytes:
        '''
        docs for logic behind peer_id 
        https://wiki.theory.org/BitTorrentSpecification#peer_id
        '''

        return ('-NA0004-' + ''.join(
            str(random.randint(0, 9)) for i in range(12))
                ).encode()
    
    def http_request(self):
        '''
        used for HTTP(S) trackers
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

        response_content = request.format_request(request_param, 
                                                  self.meta_info.announce_url)
        
        decoded_response = Decoder(response_content).decode()

        # obtain list of peers and interval - the 2 pieces of info we need
        peer_list, self.interval = request.parse_request(decoded_response)

        self.peers.extend(peer_list)

    def udp_request(self):
        '''
        used for UDP trackers - more efficient than HTTP due
        to decreased # of packets and packet size

        docs for socket initiation
        https://wiki.python.org/moin/UdpCommunication
        https://docs.python.org/3/library/socket.html#socket-timeouts
        '''

        # SOCK_DGRAM is used for UDP connections
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(5)

        # need IP address (IPv4) and port to send packet
        ip_address = socket.gethostbyname(self.meta_info.announce_url.hostname)
        port = self.meta_info.announce_url.port

        address = (ip_address, port)

        connection = UdpRequest()

        connect_response = connection.send_request(sock, 
                                                   address, 
                                                   connection.create_packet_conn())
        
        decoded_resp = connection.parse_connection(connect_response)

        request_param = {
            'connection_id' : decoded_resp['connection_id'],
            'action' : 1, # 1 for announce
            'transaction_id' : decoded_resp['transaction_id'],
            'info_hash' : self.info_hash,
            'peer_id' : self.peer_id,
            'downloaded' : self.downloaded,
            'left' : self.meta_info.length,
            'uploaded' : self.uploaded,
            'event' : 0, # 0 for none
            'IP address' : 0, # default 
            'num_want' : -1, # default
            'port' : self.port
        }

        ann_response = connection.send_request(sock, 
                                               address, 
                                               connection.create_packet_ann(request_param))
        
        decoded_ann = connection.parse_announce(ann_response)

        # necessary information is now successfully obtained
        self.interval = decoded_ann['interval']
        self.peers.extend(decoded_ann['peers'])

    def fetch_peers(self):
        scheme = self.meta_info.announce_url.scheme

        # handle http/https/udp trackers
        if scheme in 'https':
            self.http_request()
        elif scheme == 'udp':
            self.udp_request()
        else:
            raise Exception("Invalid scheme found in announce contents")