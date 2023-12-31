from metainfo import MetaInfo
import struct
from models.piece_status import PieceStatus
from models.peer import Peer
from models.piece import Piece
from models.file_writer import FileWriter
import bitstring

# class PeerConnection:
#     # optimal buffer size (for now, maybe change later?)
#     BUFFER_SIZE = 2**20

#     def __init__(self, peer: Peer, info_hash: bytes, peer_id: bytes, piece_status: PieceStatus, file_writer: FileWriter):
#         self.am_choking = True
#         self.am_interested = False
#         self.peer_choking = True
#         self.peer_interested = False

#         self.file_writer = file_writer

#         self.info_hash = info_hash
#         self.my_peer_id = peer_id

#         self.peer = peer
#         self.piece_status = piece_status

#         self.reader = None
#         self.writer = None

#         self.response = b''

#         self.curr_piece = None
#         self.know_owned_pieces = False

#     async def connect(self):
#         '''
#         establish initial connection to peer
#         and begin handshaking process
#         '''

#         await self.__open_connection()

#         # as soon as connection is made, we want to send a handshake 
#         await self.__send_handshake()

#         # get remaining response after parsing peer's handshake
#         self.response = await self.__receive_handshake()

#         print(f"Successfully connected: Peer ID is {self.peer.peer_id}")

#         await self.__send_interested()

#         await self.__handle_messages()

#     async def __send_handshake(self):
#         '''
#         docs on handshaking
#         https://wiki.theory.org/BitTorrentSpecification#Handshake

#         - 1 byte for protocol string length
#         - N bytes for protocol string
#         - 8 bytes for reserved space
#         - 20 bytes for info hash
#         - 20 bytes for peer id

#         BitTorrent standard protocol string is 
#         'BitTorrent protocol'

#         total length is 68 bytes
#         '''

#         handshake = struct.pack('>B19s8x20s20s', *[
#             19,
#             b'BitTorrent protocol',
#             self.info_hash,
#             self.my_peer_id
#         ])

#         self.writer.write(handshake)
#         await self.writer.drain()
    
#     async def __receive_handshake(self):
#         response = await asyncio.wait_for(self.reader.readexactly(1), 180)

#         pstrlen = struct.unpack('>B', response)[0]

#         response = await asyncio.wait_for(self.reader.readexactly(pstrlen + 48), 180)

#         pstr, reserved, info_hash, peer_id = struct.unpack('>%dsQ20s20s' % pstrlen, response)

#         if pstr != b'BitTorrent protocol':
#             self.close_connection()
#             return

#         # peer ID received should never match client peer ID
#         if peer_id == self.my_peer_id:
#             self.close_connection()
#             return

#         # TODO: when HTTP response isn't in compact mode, make sure
#         # to save peer ID so that it can be verified here

#         # peer ID should never change for any given peer
#         if self.peer.peer_id is not None and self.peer.peer_id != peer_id:
#             self.close_connection()
#             return
        
#         if info_hash != self.info_hash:
#             self.close_connection()
#             return

#         self.peer.info_hash = info_hash
#         self.peer.peer_id = peer_id

#         return response[68:]

#     async def __open_connection(self):
#         '''
#         used to create the connection with peer
#         '''

#         self.reader, self.writer = await asyncio.open_connection(self.peer.host,
#                                                                  self.peer.port)
        
#     async def close_connection(self):
#         self.writer.close()
#         await self.writer.wait_closed()
        
#     async def __handle_messages(self):
#         '''
#         docs for different types of messages
#         https://wiki.theory.org/BitTorrentSpecification#Messages
#         '''

#         while True:
#             response = await asyncio.wait_for(self.reader.readexactly(4), 180)

#             length = struct.unpack('>I', response)[0]

#             # keep alive message
#             if length == 0:
#                 continue

#             response = await asyncio.wait_for(self.reader.readexactly(length), 180)

#             message_id = struct.unpack('>B', response[:1])[0]
#             payload = response[1:]

#             # print(f"Length: {length}")
#             # print(f"Message ID: {message_id}")
#             # print(f"Payload Size: {len(payload)}")

#             # for us to request pieces, we need to be interested & unchoked
#             if message_id == 0:
#                 self.am_choking = True
#             elif message_id == 1:
#                 self.am_choking = False
#             elif message_id == 2:
#                 self.peer_interested = True
#             elif message_id == 3:
#                 self.peer_interested = False
#             elif message_id == 4:
#                 await self.__handle_have(payload)
#                 self.know_owned_pieces = True
#             elif message_id == 5:
#                 await self.__handle_bitfield(payload)
#                 self.know_owned_pieces = True
#             elif message_id == 6: # TODO: we're currently only leechers
#                 await self.__handle_request(payload)
#             elif message_id == 7:
#                 await self.__handle_piece(payload)
#             elif message_id == 8: # TODO: we're currently only leechers
#                 await self.__handle_cancel(payload) 
#             elif message_id == 9:
#                 pass

#             if self.am_interested and not self.am_choking and self.know_owned_pieces:
#                 await self.__send_request()

#     async def __handle_have(self, payload: bytes):
#         index = struct.unpack('>I', payload)[0]
#         self.piece_status.update_peers_own(index, self.peer)

#     async def __handle_bitfield(self, payload: bytes):
#         piece_bits = bitstring.BitArray(payload).bin

#         for bit in piece_bits:
#             index = int(bit)

#             if piece_bits[index]:
#                 self.piece_status.update_peers_own(index, self.peer)

#     async def __send_interested(self):
#         message = struct.pack('>IB', 1, 2)

#         self.writer.write(message)
#         await self.writer.drain()

#         self.am_interested = True

#     async def __handle_piece(self, payload: bytes):
#         '''
#         unpack the block and update piece status
#         '''

#         block_len = len(payload) - 8

#         index, begin = struct.unpack('>II', payload[:8])
#         block = struct.unpack('%ds' % block_len, payload[8:])[0]

#         # write to the file
#         self.file_writer.write(index, begin, block)

#         self.curr_piece.block_index += 1

#         # if we've downloaded the file, we're done with it
#         if self.curr_piece.is_downloaded():
#             print("Finished piece")
#             self.piece_status.update_completed_pieces(index)
#             self.curr_piece = None

#     async def __send_request(self):
#         new_piece = False
        
#         if self.curr_piece is None or self.curr_piece.is_downloaded():
#             self.curr_piece = self.piece_status.choose_next_piece(self.peer)

#             # return early if there're no more missing pieces offered by peer
#             if self.curr_piece is None:
#                 return
            
#             new_piece = True

#         # TODO: implement a rarest first downloading strategy instead of
#         # randomly choosing
            
#         index = self.piece_status.get_piece_index(self.curr_piece)
#         begin = self.curr_piece.get_byte_offset()
#         length = self.curr_piece.get_block_size()

#         if new_piece:
#             self.piece_status.update_ongoing_pieces(index)

#         message = struct.pack('>IBIII', *[
#             13,
#             6,
#             index,
#             begin,
#             length
#         ])

#         self.writer.write(message)
#         await self.writer.drain()


from twisted.internet.protocol import Protocol, Factory

class PeerProtocol(Protocol):
    def __init__(self, factory, peer: Peer):
        self.factory = factory
        self.peer = peer

        self.am_choked = True
        self.am_interested = False

        self.peer_choked = True
        self.peer_interested = False

        self.response = b''
        self.remaining_message_len = 0

        self.have_handshaked = False
        self.peer_shared_pieces = False

        self.curr_piece = None

        self.bitfield = bitstring.BitArray(self.factory.piece_status.num_pieces)

    def connectionMade(self):
        '''
        once a connection is made, initiate by sending a handshake
        '''
        # print("Connection made")
        # self.send_handshake()

    def connectionLost(self, reason):
        if self.curr_piece:
            print("Connection has been lost at index %d" % self.curr_piece.block_index)
        else:
            print("Connection has been lost")

    def dataReceived(self, data: bytes) -> None:
        if not self.have_handshaked:
            self.receive_handshake(data)
        else:
            self.parse_message(data)

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

        handshake = struct.pack('>B19s8x20s20s', *[
            19,
            b'BitTorrent protocol',
            self.factory.info_hash,
            self.factory.my_peer_id
        ])

        self.transport.write(handshake)

    def receive_handshake(self, data: bytes):
        pstrlen = struct.unpack('>B', data[:1])[0]

        pstr, reserved, info_hash, peer_id = struct.unpack('>%dsQ20s20s' % pstrlen, data[1:68])

        if pstr != b'BitTorrent protocol':
            self.transport.loseConnection()
            return

        # peer ID received should never match client peer ID
        if peer_id == self.factory.my_peer_id:
            self.transport.loseConnection()
            return

        # TODO: when HTTP response isn't in compact mode, make sure
        # to save peer ID so that it can be verified here

        # peer ID should never change for any given peer
        if self.peer.peer_id is not None and self.peer.peer_id != peer_id:
            self.transport.loseConnection()
            return

        self.peer.info_hash = info_hash
        self.peer.peer_id = peer_id

        self.have_handshaked = True

        self.send_interested()

    def parse_message(self, response: bytes):
        '''
        sometimes messages aren't sent in full so we need to parse
        the message and send once we have the full message
        '''

        # if it's not a valid message
        if len(response) < 4:
            return
        
        # if it's a new message
        if self.remaining_message_len == 0:
            length = struct.unpack('>I', response[:4])[0]

            # keep alive message
            if length == 0:
                return
            elif length == 1: # message with no payload - just message_id
                self.handle_message(response[:5])
                self.parse_message(response[5:])
            else: # full message 
                # there's overflow if the expected length exceeds actual length
                overflow = length > len(response[4:])

                if overflow:
                    self.remaining_message_len = length - len(response[4:])
                    self.response += response
                else:
                    self.handle_message(response[:length + 4])
                    self.parse_message(response[length + 4:])
        else: # if it's continuing previous message
            overflow = self.remaining_message_len > len(response)

            if overflow:
                self.remaining_message_len -= len(response)
                self.response += response
            else:
                self.response += response[:self.remaining_message_len]
                self.handle_message(self.response)

                new_message = response[self.remaining_message_len:]
                self.remaining_message_len = 0
                self.response = b''

                self.parse_message(new_message)


    def handle_message(self, response: bytes):
        length, message_id = struct.unpack('>IB', response[:5])

        payload = response[5:]

        # print(f"Length: {length}")
        # print(f"Message ID: {message_id}")
        # print(f"Payload Size: {len(payload)}")

        # for us to request pieces, we need to be interested & unchoked
        if message_id == 0:
            self.am_choked = True
        elif message_id == 1:
            self.am_choked = False
        elif message_id == 2:
            self.peer_interested = True
        elif message_id == 3:
            self.peer_interested = False
        elif message_id == 4:
            self.handle_have(payload)
            self.peer_shared_pieces = True
        elif message_id == 5:
            self.handle_bitfield(payload)
            self.peer_shared_pieces = True
        elif message_id == 6: # TODO: we're currently only leechers
            self.handle_request(payload)
        elif message_id == 7:
            self.handle_piece(payload)
        elif message_id == 8: # TODO: we're currently only leechers
            self.handle_cancel(payload) 
        elif message_id == 9:
            pass

        if self.am_interested and not self.am_choked and self.peer_shared_pieces:
            self.send_request()

    def send_interested(self):
        message = struct.pack('>IB', 1, 2)
        self.transport.write(message)

        self.am_interested = True

    def handle_have(self, payload: bytes):
        index = struct.unpack('>I', payload)[0]
        # self.factory.piece_status.update_peers_own(index, self.peer)

        self.bitfield[index] = 1

        # make sure we're still interested
        if not self.am_interested:
            self.send_interested()

    def handle_bitfield(self, payload: bytes):
        # piece_bits = bitstring.BitArray(payload).bin

        # for bit in piece_bits:
        #     index = int(bit)

        #     if piece_bits[index]:
        #         self.factory.piece_status.update_peers_own(index, 
        #                                                    self.peer)
                
        piece_bits = bitstring.BitArray(payload)

        self.bitfield = piece_bits[:piece_bits.len] + self.bitfield[piece_bits.len:]

        # send interested message after receiving bitfield
        if not self.am_interested:
            self.send_interested()

    def handle_piece(self, payload: bytes):
        '''
        unpack the block and update piece status
        '''

        # TODO: do something with this / clean it up
        if (len(payload) - 8) % self.curr_piece.BLOCK_SIZE != 0:
            return
        
        # print("BLOCK INDEX %d / %d total blocks" % (self.curr_piece.block_index, self.curr_piece.num_blocks))

        index, begin = struct.unpack('>II', payload[:8])

        # write to the file
        # self.factory.file_writer.write(index, begin, block)

        self.curr_piece.block_index += 1

        # if we've downloaded the file, we're done with it
        if self.curr_piece.is_downloaded():
            print("FINISHED PIECE")
            self.factory.piece_status.update_completed_pieces(index)
            self.curr_piece = None

    def send_request(self):
        new_piece = False

        if self.curr_piece is None or self.curr_piece.is_downloaded():
            # self.curr_piece = self.factory.piece_status.choose_next_piece(self.peer)
            self.curr_piece = self.factory.piece_status.choose_next_piece(self.bitfield)

            # if there're no more missing pieces offered by peer
            if self.curr_piece is None:
                # we're no longer interested as peer owns no desired pieces
                self.am_interested = False
                return
            
            new_piece = True

        # TODO: implement a rarest first downloading strategy instead of
        # randomly choosing
            
        index = self.factory.piece_status.get_piece_index(self.curr_piece)
        begin = self.curr_piece.get_byte_offset()
        length = self.curr_piece.get_block_size()

        # print("Requesting Offset: %d" % begin)
        # print("Requesting a block size of: %d" % length)

        if new_piece:
            self.factory.piece_status.update_ongoing_pieces(index)

        message = struct.pack('>IBIII', *[
            13,
            6,
            index,
            begin,
            length
        ])

        self.transport.write(message)

    # TODO: currently only leechers
    def handle_request(self, payload: bytes):
        pass

    # TODO: currently only leechers
    def handle_cancel(self, payload: bytes):
        pass

class PeerFactory(Factory):
    def __init__(self, peers: list, 
                 info_hash: bytes, 
                 peer_id: bytes, 
                 piece_status: PieceStatus, 
                 file_writer: FileWriter):
        
        self.info_hash = info_hash
        self.my_peer_id = peer_id

        self.piece_status = piece_status
        self.file_writer = file_writer

        self.peers = peers

    def buildProtocol(self, addr):
        return PeerProtocol(self)