from metainfo import MetaInfo
import struct
from models.peer import Peer
from models.piece import Piece
import bitstring
from twisted.internet.protocol import Protocol, Factory
from twisted.internet import reactor
import os
import tqdm
import random

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

        self.progress_bar = tqdm.tqdm(total=self.num_pieces, initial=0, unit='pieces')

        self.completed_pieces = bitstring.BitArray(self.num_pieces)
        self.ongoing_pieces = bitstring.BitArray(self.num_pieces)
        self.missing_pieces = bitstring.BitArray(self.num_pieces)
        # bitarray should start with all 1s as all pieces are missing
        self.missing_pieces.invert()

        self.data = [b'' for _ in range(self.num_pieces)]

    def update_completed_pieces(self, index: int):
        self.completed_pieces.set(1, index)
        self.missing_pieces.set(0, index)

    def get_rarest_piece(self, bitfield: bitstring.BitArray) -> Piece | None:
        # create intersection of pieces that peer owns and are missing
        desired_pieces = bitfield & self.missing_pieces
        piece_indices = list(desired_pieces.findall(bitstring.Bits('0b1')))

        if len(piece_indices) == 0:
            return None

        index = random.choice(piece_indices)

        return self.pieces[index]
    
    def get_file_path(self, path):
        file_name = path.pop()
        directory = os.path.join(os.getcwd(), 'downloads', *path)

        if len(path) > 0:
            os.makedirs(directory)
        
        file_path = directory + '/' + file_name

        return open(file_path, 'wb')
    
    def write(self):
        if self.multi_files:
            self.__write_multi_files()
        else:
            self.__write_file()
    
    def __write_file(self):
        file = self.get_file_path([self.meta_info.name])

        for index in range(self.num_pieces):
            data = self.data[index]
            file.write(data)

    def __write_multi_files(self):
        file_offset = 0
        file_index = 0
        file_len = self.meta_info.files[file_index]['length']
        file = self.get_file_path(self.meta_info.files[file_index]['path'])

        for index in range(self.num_pieces):
            data = self.data[index]
            data_len = len(self.data[index])

            # piece won't all fit in file
            if data_len + file_offset > file_len:
                remaining_file_len = file_len - file_offset
                curr_file_data = data[:remaining_file_len]
                remaining_data = data[remaining_file_len:]

                file.write(curr_file_data)
                file.close()

                file_index += 1
                file_offset = 0
                file_len = self.meta_info.files[file_index]['length']
                file = self.get_file_path(self.meta_info.files[file_index]['path'])

                file.write(remaining_data)
                file_offset += len(remaining_data)
            else:
                file.write(data)
                file_offset += data_len

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
        self.block_index = 0

        self.bitfield = bitstring.BitArray(self.factory.num_pieces)

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

        # if there's more in the message than just handshake
        if len(data) - 68 > 0:
            self.parse_message(data[68:])

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
                self.attempt_request()
                return
            elif length == 1: # message with no payload - just message_id
                self.handle_message(response[4:])
                self.parse_message(response[5:])
            else: # full message 
                # there's overflow if the expected length exceeds actual length
                overflow = length > len(response[4:])

                if overflow:
                    self.remaining_message_len = length - len(response[4:])
                    self.response += response
                else:
                    self.handle_message(response[4:length + 4])
                    self.parse_message(response[length + 4:])
        else: # if it's continuing previous message
            overflow = self.remaining_message_len > len(response)

            if overflow:
                self.remaining_message_len -= len(response)
                self.response += response
            else:
                self.response += response[:self.remaining_message_len]
                self.handle_message(self.response[4:])

                new_message = response[self.remaining_message_len:]
                self.remaining_message_len = 0
                self.response = b''

                self.parse_message(new_message)


    def handle_message(self, response: bytes):
        message_id = struct.unpack('B', response[:1])[0]
        payload = response[1:]

        # for us to request pieces, we need to be interested & unchoked
        if message_id == 0:
            self.am_choked = True
            # try to get unchoked
            self.send_interested()
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

        self.attempt_request()

    def send_interested(self):
        message = struct.pack('>IB', 1, 2)
        self.transport.write(message)

        self.am_interested = True

    def handle_have(self, payload: bytes):
        index = struct.unpack('>I', payload)[0]

        self.bitfield.set(1, index)

        # make sure we're still interested
        if not self.am_interested:
            self.send_interested()

    def handle_bitfield(self, payload: bytes):
        piece_bits = bitstring.BitArray(payload)

        split = min(self.bitfield.len, piece_bits.len)

        self.bitfield = piece_bits[:split] + self.bitfield[split:]

        # send interested message after receiving bitfield
        if not self.am_interested:
            self.send_interested()

    def handle_piece(self, payload: bytes):
        '''
        unpack the block and update piece status
        '''

        if not self.curr_piece:
            return

        # TODO: clean this up so we can send a cancel message?
        if self.factory.completed_pieces[self.curr_piece.index]:
            self.curr_piece = None
            self.curr_bytes = b''
            self.block_index = 0
            return

        block_len = len(payload) - 8

        index, begin = struct.unpack('>II', payload[:8])

        block = struct.unpack('%ds' % block_len, payload[8:])[0]

        # add to current piece contents
        self.curr_bytes += block
        self.block_index += 1

        # if we've downloaded the piece, we're done with it
        if self.curr_piece.is_downloaded(self.block_index):
            if not self.factory.completed_pieces[self.curr_piece.index]:
                self.factory.data[index] = self.curr_bytes
                self.factory.progress_bar.update(1)
                self.factory.update_completed_pieces(index)
            
            self.curr_piece = None
            self.curr_bytes = b''
            self.block_index = 0

            # if all pieces are completed, end all connections
            if self.factory.completed_pieces.all(True):
                self.factory.write()
                print("\nDownload has completed successfully!")
                reactor.stop()

    def attempt_request(self):
        '''
        attempt to send a request if requirements are met
        '''

        if (self.am_interested 
            and not self.am_choked 
            and self.peer_shared_pieces 
            and self.curr_piece is None):
            self.send_request()

    def send_request(self):
        '''
        sends peer a request for an entire piece that's chosen at random
        '''

        self.curr_piece = self.factory.get_rarest_piece(self.bitfield)

        # couldn't find any piece based on peer's bitfield
        if self.curr_piece is None:
            return
        
        piece_index = self.curr_piece.index

        for block_index in range(0, self.curr_piece.num_blocks):
            begin = block_index * self.curr_piece.BLOCK_SIZE

            if self.curr_piece.on_final_block(block_index):
                length = self.curr_piece.final_block_size
            else:
                length = self.curr_piece.BLOCK_SIZE

            message = struct.pack('>IBIII', *[
                13,
                6,
                piece_index,
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