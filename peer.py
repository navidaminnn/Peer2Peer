from metainfo import MetaInfo
import struct
import asyncio

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

        self.info_hash = info_hash
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
        self.writer.write(self.send_handshake())
        await self.writer.drain()

        # TODO: figure out if there's a more optimal buffer size
        response = await self.reader.read(2**16)

        # TODO: is this needed? if so, figure out cleaner way to handle than raising exception
        if not response:
            raise ConnectionError('Unable to receive handshake from peer')
            
        self.receive_handshake(response)

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

        total length is 68 bytes
        '''

        return struct.pack('>B19s8x20s20s', *[
            19,
            b'BitTorrent protocol',
            self.info_hash,
            self.own_peer_id
        ])
    
    def receive_handshake(self, response: bytes):
        # unpack string length and use it to unpack rest of handshake
        pstrlen = struct.unpack('>B', response[:1])

        pstr, reserved, info_hash, peer_id = struct.unpack('>%dsQ20s20s' % pstrlen, response[1:68])

        # TODO: fix all of these if statements to call a proper
        # connection closing function

        if pstr != b'BitTorrent protocol':
            self.writer.close()
            raise ConnectionError('Incorrect connection')

        # peer ID received should never match client peer ID
        if peer_id == self.own_peer_id:
            self.writer.close()
            raise ConnectionError('Incorrect connection')

        # peer ID should never change for any given peer
        if self.peer.peer_id is not None and self.peer.peer_id != peer_id:
            self.writer.close()
            raise ConnectionError('Incorrect connection')
        
        if info_hash != self.info_hash:
            self.writer.close()
            raise ConnectionError('Incorrect connection')

        self.peer.info_hash = info_hash
        self.peer.peer_id = peer_id
    
    def send_message(self):
        pass