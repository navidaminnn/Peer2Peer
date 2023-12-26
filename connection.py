from metainfo import MetaInfo
import struct
import asyncio
from utils.piece_status import PieceStatus
from utils.peer import Peer
from utils.piece import Piece
import bitarray

class PeerConnection:
    # optimal buffer size (for now, maybe change later?)
    BUFFER_SIZE = 2**16

    def __init__(self, peer: Peer, info_hash: bytes, peer_id: bytes, piece_status: PieceStatus):
        self.am_choking = True
        self.am_interested = False
        self.peer_choking = True
        self.peer_interested = False

        self.info_hash = info_hash
        self.my_peer_id = peer_id

        self.peer = peer
        self.piece_status = piece_status

        self.reader = None
        self.writer = None

        self.response = b''

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

        await self.handle_messages()

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

        if pstr != b'BitTorrent protocol':
            self.__close_connection()
            return

        # peer ID received should never match client peer ID
        if peer_id == self.my_peer_id:
            self.__close_connection()
            return

        # TODO: when HTTP response isn't in compact mode, make sure
        # to save peer ID so that it can be verified here

        # peer ID should never change for any given peer
        if self.peer.peer_id is not None and self.peer.peer_id != peer_id:
            self.__close_connection()
            return
        
        if info_hash != self.info_hash:
            self.__close_connection()
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
        
    async def __close_connection(self):
        self.writer.close()
        await self.writer.wait_closed()
        
    async def handle_messages(self):
        '''
        docs for different types of messages
        https://wiki.theory.org/BitTorrentSpecification#Messages
        '''

        while True and len(self.response) != 0:
            length = struct.unpack('>I', self.response[:1])

            # keep alive message
            if length == 0:
                self.response = self.response[1:]
                continue

            message_id = struct.unpack('>B', self.response[1:5])

            self.response = self.response[5:]

            payload = self.response[:length-1]

            # for us to request pieces, we need to be interested & unchoked
            if message_id == 0:
                self.am_choking = True
            elif message_id == 1:
                self.am_choking = False
            elif message_id == 2:
                self.peer_interested = True
            elif message_id == 3:
                self.peer_interested = False
            elif message_id == 4:
                self.__handle_have(payload)
            elif message_id == 5:
                self.__handle_bitfield(payload)
            elif message_id == 6: # TODO: we're currently only leechers
                self.__handle_request(payload)
            elif message_id == 7:
                self.__handle_piece(payload)
            elif message_id == 8: # TODO: we're currently only leechers
                self.__handle_cancel(payload) 
            elif message_id == 9:
                pass

            self.response = self.response[length-1:]

    async def __handle_have(self, payload: bytes):
        index = struct.unpack('>I', payload)
        self.piece_status.update_peers_own(index, self.peer)

    async def __handle_bitfield(self, payload: bytes):
        bitfield = struct.unpack('>%ds' % len(payload), payload)

        print(bitfield)

    async def __handle_request(self, payload: bytes):
        index, begin, length = struct.unpack('>III', payload)

        # TODO: send a piece message to fulfill the request

    async def __handle_piece(self, payload: bytes):
        block_len = len(payload) - 8

        index, begin = struct.unpack('>II', payload[:8])
        block = struct.unpack('%ds' % block_len, payload[8:])

        # self.piece_status.update_ongoing_pieces(index)

        # TODO: create file writer and write the block to the file    

    async def __handle_cancel(self, payload: bytes):
        pass

    async def __send_interested(self):
        message = struct.pack('>IB', 1, 2)

        self.writer.write(message)
        await self.writer.drain()

    async def __send_request(self):
        # TODO: implement a rarest first downloading strategy instead of
        # randomly choosing

        chosen_piece = self.piece_status.choose_next_piece(self.peer)
        index = self.piece_status.get_piece_index(chosen_piece)
        begin = chosen_piece.block_to_download
        length = chosen_piece.get_block_size()

        message = struct.pack('>IBIII', *[
            13,
            6,
            index,
            begin,
            length
        ])

        self.writer.write(message)
        await self.writer.drain()