from metainfo import MetaInfo
import struct
import asyncio
# from peer import Peer

CHOKE = 0
UNCHOKE = 1
INTERESTED = 2
NOT_INTERESTED = 3
HAVE = 4
BITFIELD = 5
REQUEST = 6
PIECE = 7
CANCEL = 8
PORT = 9

class Peer:
    def __init__(self, ip_address: str):
        self.host, self.port = ip_address.rsplit(':', 1)

        self.info_hash = None
        self.peer_id = None

class PeerConnection:
    def __init__(self, peer_info: str, info_hash: bytes, peer_id: bytes):
        self.am_choking = True
        self.am_interested = False
        self.peer_choking = True
        self.peer_interested = False

        self.own_info_hash = info_hash
        self.own_peer_id = peer_id

        self.peer = Peer(peer_info)

        self.reader = None
        self.writer = None

    async def connect(self):
        '''
        establish initial conncetion to peer
        '''

        self.reader, self.writer = await asyncio.open_connection(self.peer.host, 
                                                                 self.peer.port)

        # as soon as connection is made, we want to send a handshake
        self.send_handshake()
        self.receive_handshake()

        print("Peer's ID " + self.peer.peer_id)
        print("Peer's info hash " + self.peer.info_hash)

    def send_handshake(self):
        '''
        docs on handshaking
        https://wiki.theory.org/BitTorrentSpecification#Handshake

        - 1 byte for protocol string length
        - N bytes for protocol string
        - 8 bytes for reserved space
        - 20 bytes for info hash
        - 20 bytes for peer id

        BitTorrent standard protocol string is 
        'BitTorrent protocol'
        '''

        return struct.pack('>B19sQ20s20s', *[
            '19',
            'BitTorrent protocol',
            0,
            self.own_info_hash,
            self.own_peer_id
        ])
    
    def receive_handshake(self, response: bytes):
        # unpack string legnth and use it to unpack rest of handshake
        pstrlen = struct.unpack('>B', response[:1])

        pstr, reserved, info_hash, peer_id = struct.unpack('>%dsQ20s20s', pstrlen, response[1:])

        if pstr != 'BitTorrent protocol':
            self.writer.close()

        # peer ID received should never match client peer ID
        if peer_id == self.own_peer_id:
            self.writer.close()

        # peer ID should never change for any given peer
        if self.peer.peer_id is not None and self.peer.peer_id != peer_id:
            self.writer.close()

        self.peer.info_hash = info_hash
        self.peer.peer_id = peer_id
    
    def send_message(self):
        pass