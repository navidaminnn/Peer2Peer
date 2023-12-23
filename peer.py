from metainfo import MetaInfo
import struct
import asyncio
from utils.piece_status import PieceStatus

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
    # optimal buffer size (for now, maybe change later?)
    BUFFER_SIZE = 2**16

    def __init__(self, peer_info: str, info_hash: bytes, peer_id: bytes, piece_status: PieceStatus):
        self.am_choking = True
        self.am_interested = False
        self.peer_choking = True
        self.peer_interested = False

        self.info_hash = info_hash
        self.my_peer_id = peer_id

        self.peer = Peer(peer_info)
        self.piece_status = piece_status

        self.reader = None
        self.writer = None

        self.response = None

    async def connect(self):
        '''
        establish initial connection to peer
        and begin handshaking process
        '''

        await self.__open_connection()

        # as soon as connection is made, we want to send a handshake
        await self.send_handshake()

        # get remaining response after parsing peer's handshake
        self.response = await self.receive_handshake()

        print(f"Peer ID: {self.peer.peer_id}")
        print(f"Peer Info Hash: {self.peer.info_hash}")
        print(f"Remaining response: {self.response}")

        self.handle_messages()

    async def send_handshake(self):
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

        handshake = struct.pack('>B19s8x20s20s', *[
            19,
            b'BitTorrent protocol',
            self.info_hash,
            self.my_peer_id
        ])

        self.writer.write(handshake)
        await self.writer.drain()
    
    async def receive_handshake(self):
        response = await self.reader.read(self.BUFFER_SIZE) 

        if not response:
            raise ConnectionError('Unable to receive handshake from peer')

        # unpack string length and use it to unpack rest of handshake
        pstrlen = struct.unpack('>B', response[:1])

        pstr, reserved, info_hash, peer_id = struct.unpack('>%dsQ20s20s' % pstrlen, response[1:68])

        # TODO: fix all of these if statements to properly
        # close connection

        if pstr != b'BitTorrent protocol':
            self.writer.close()
            return

        # peer ID received should never match client peer ID
        if peer_id == self.my_peer_id:
            self.writer.close()
            return

        # TODO: when HTTP response isn't in compact mode, make sure
        # to save peer ID so that it can be verified here

        # peer ID should never change for any given peer
        if self.peer.peer_id is not None and self.peer.peer_id != peer_id:
            self.writer.close()
            return
        
        if info_hash != self.info_hash:
            self.writer.close()
            return

        self.peer.info_hash = info_hash
        self.peer.peer_id = peer_id

        return response[68:]

    async def __open_connection(self):
        '''
        used to create the connection with peer
        '''

        self.reader, self.writer = await asyncio.open_connection(self.peer.host,
                                                                 self.peer.port)
        
    async def handle_messages(self):
        '''
        docs for different types of messages
        https://wiki.theory.org/BitTorrentSpecification#Messages
        '''

        while True:
            len, message_id = struct.unpack('>IB', self.response[:5])

            self.response = self.response[5:]

            if message_id == 0:
                self.am_choking = True
            elif message_id == 1:
                self.am_choking = False
            elif message_id == 2:
                self.am_interested = True
            elif message_id == 3:
                self.am_interested = False
            elif message_id == 4:
                self.__handle_have()
            elif message_id == 5:
                self.__handle_bitfield()
            elif message_id == 6:
                self.__handle_request()
            elif message_id == 7:
                self.__handle_piece()
            elif message_id == 8:
                pass
            elif message_id == 9:
                pass
            elif len == 0: # keep alive
                pass

            self.response = self.response[len:]

    async def __handle_have(self):
        index = struct.unpack('>I', self.response)
