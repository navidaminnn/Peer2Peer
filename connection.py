from metainfo import MetaInfo
import struct
from models.peer import Peer
from models.piece import Piece
import bitstring
from twisted.internet.protocol import Protocol, Factory
from twisted.internet import reactor
import os
import tqdm

class PeerFactory(Factory):
    def __init__(self, 
                 peers: list, 
                 meta_info: MetaInfo, 
                 peer_id: bytes):
        self.meta_info = meta_info
        self.info_hash = meta_info.info_hash
        self.my_peer_id = peer_id

        self.peers = peers

        self.pieces = meta_info.pieces
        self.num_pieces = meta_info.num_pieces
        self.file_size = meta_info.length
        self.multi_files = meta_info.multi_files

        self.progress_bar = tqdm.tqdm(total=self.num_pieces, initial=0)

        self.completed_pieces = bitstring.BitArray(self.num_pieces)
        self.ongoing_pieces = bitstring.BitArray(self.num_pieces)
        self.missing_pieces = bitstring.BitArray(self.num_pieces)
        # bitarray should start with all 1s as all pieces are missing
        self.missing_pieces.invert() 

        # keep track of # of peers that own a given piece
        self.num_peers_own = [0 for _ in range(self.num_pieces)]

    def update_ongoing_pieces(self, index: int):
        self.ongoing_pieces.set(1, index)
        self.missing_pieces.set(0, index)

    def update_completed_pieces(self, index: int):
        self.completed_pieces.set(1, index)
        self.ongoing_pieces.set(0, index)

    def update_peers_own(self, bitfield: bitstring.BitArray):
        for i in range(self.num_pieces):
            if bitfield[i]:
                self.num_peers_own[i] += 1

    def add_peers_own(self, index: int):
        self.num_peers_own[index] += 1

    def get_rarest_piece(self, bitfield: bitstring.BitArray) -> Piece | None:
        rarest = None
        min_occurance = len(self.peers)

        for i in range(self.num_pieces):
            # if peer owns the piece and it's missing
            if bitfield[i] and self.missing_pieces[i]:
                if self.num_peers_own[i] < min_occurance:
                    rarest = self.pieces[i]
                    min_occurance = self.num_peers_own[i]
        
        return rarest
    
    def write(self, piece_index: int, piece_byte_offset: int, data: bytes):
        total_offset = self.meta_info.piece_length * piece_index + piece_byte_offset

        if not self.multi_files:
            file_path = os.path.join('downloads/' + self.meta_info.name)

            with open(file_path, 'wb') as f:
                f.seek(total_offset)
                f.write(data)
        else:
            total_file_len = 0

            for file in self.meta_info.files:
                file_name = file['path']
                file_len = file['length']

                if total_file_len + file_len > total_offset:
                    break

                total_file_len += file_len

            # write data to file at file offset
            file_offset = total_offset - total_file_len

            is_leftover = len(data) + file_offset > file_len

            # there's not enough space in file for all data
            if is_leftover:
                remaining_file_len = file_len - file_offset
                data = data[:remaining_file_len]
                remaining_data = data[remaining_file_len:]

            file_path = os.path.join('downloads/' + file_name)

            with open(file_path, 'wb') as f:
                f.seek(file_offset)
                f.write(data)

            # recursive call if there's not enough space in file for data
            if is_leftover:
                leftover_bytes = piece_byte_offset + remaining_file_len

                self.write(piece_index, leftover_bytes, remaining_data)

    def buildProtocol(self, addr):
        return PeerProtocol(self)

class PeerProtocol(Protocol):
    def __init__(self, factory: PeerFactory, peer: Peer):
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
        self.curr_bytes = b''

        self.bitfield = bitstring.BitArray(self.factory.num_pieces)

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
                # self.handle_message(response[:5])
                self.handle_message(response[4:])
                self.parse_message(response[5:])
            else: # full message 
                # there's overflow if the expected length exceeds actual length
                overflow = length > len(response[4:])

                if overflow:
                    self.remaining_message_len = length - len(response[4:])
                    self.response += response
                else:
                    # self.handle_message(response[:length + 4])
                    self.handle_message(response[4:length + 4])
                    self.parse_message(response[length + 4:])
        else: # if it's continuing previous message
            overflow = self.remaining_message_len > len(response)

            if overflow:
                self.remaining_message_len -= len(response)
                self.response += response
            else:
                self.response += response[:self.remaining_message_len]
                # self.handle_message(self.response)
                self.handle_message(self.response[4:])

                new_message = response[self.remaining_message_len:]
                self.remaining_message_len = 0
                self.response = b''

                self.parse_message(new_message)


    def handle_message(self, response: bytes):
        # length, message_id = struct.unpack('>IB', response[:5])
        message_id = struct.unpack('B', response[:1])[0]

        # payload = response[5:]
        payload = response[1:]

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

        self.bitfield[index] = 1

        self.factory.add_peers_own(index)

        # make sure we're still interested
        if not self.am_interested:
            self.send_interested()

    def handle_bitfield(self, payload: bytes):
        piece_bits = bitstring.BitArray(payload)

        self.bitfield = piece_bits[:piece_bits.len] + self.bitfield[piece_bits.len:]

        self.factory.update_peers_own(self.bitfield)

        # send interested message after receiving bitfield
        if not self.am_interested:
            self.send_interested()

    def handle_piece(self, payload: bytes):
        '''
        unpack the block and update piece status
        '''

        block_len = len(payload) - 8

        # TODO: do something with this / clean it up
        if block_len % self.curr_piece.BLOCK_SIZE != 0:
            return

        index, begin = struct.unpack('>II', payload[:8])

        block = struct.unpack('%ds' % block_len, payload[8:])[0]

        # write to the file
        # self.factory.write(index, begin, block)
        self.curr_bytes += block

        self.curr_piece.block_index += 1

        # if we've downloaded the piece, we're done with it
        if self.curr_piece.is_downloaded():
            self.factory.write(index, 0, self.curr_bytes)
            self.factory.progress_bar.update(1)
            self.factory.update_completed_pieces(index)
            
            self.curr_piece = None
            self.curr_bytes = b''

            # if all pieces are completed, end all connections
            if self.factory.completed_pieces.all(1):
                reactor.stop()

    def send_request(self):
        new_piece = False

        if self.curr_piece is None or self.curr_piece.is_downloaded():
            self.curr_piece = self.factory.get_rarest_piece(self.bitfield)

            # if there're no more missing pieces offered by peer
            if self.curr_piece is None:
                # we're no longer interested as peer owns no desired pieces
                self.am_interested = False
                return
            
            new_piece = True
        
        index = self.curr_piece.index
        begin = self.curr_piece.get_byte_offset()
        length = self.curr_piece.get_block_size()

        if new_piece:
            self.factory.update_ongoing_pieces(index)

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