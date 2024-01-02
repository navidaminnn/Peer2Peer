from utils.bencoding import Decoder, Encoder
import hashlib
import urllib.parse
from models.piece import Piece

class MetaInfo:
    def __init__(self, file_name: str):
        self.file_name = file_name
        self.multi_files = False

        with open(file_name, 'rb') as file:
            self.file_contents = Decoder(file.read()).decode()

    def parse_file(self):
        '''
        docs for understanding file structure
        https://wiki.theory.org/BitTorrentSpecification#Metainfo_File_Structure
        '''

        # first parse all the info that is consistent whether it's single file or multi file

        # decode announce contents so it can be urlparsed as a string
        decoded_announce = self.file_contents[b'announce'].decode()
        self.announce_url = urllib.parse.urlparse(decoded_announce)

        self.info = self.file_contents[b'info']

        # info hash will be used for tracker later on
        self.info_hash = hashlib.sha1(Encoder().encode(self.info)).digest()

        # check for all optional contents
        if b'announce-list' in self.file_contents:
            self.announce_list = self.file_contents[b'announce-list']

        if b'creation date' in self.file_contents:
            self.creation_date = self.file_contents[b'creation date']

        if b'encoding' in self.file_contents:
            self.encoding = self.file_contents[b'encoding']

        # now check for everything in info dict
        self.num_pieces = len(self.info[b'pieces']) // 20
        self.piece_length = self.info[b'piece length']
        self.name = self.info[b'name'].decode()

        # check for multi-file specific contents in info dict
        if b'files' in self.info:
            self.multi_files = True
            self.files = []

        # check for specific contents in info dict depending on if multi-file
        if self.multi_files:
            self.length = 0

            for file in self.info[b'files']:
                self.length += file[b'length']
                self.files.append({'length':file[b'length'], 'path':file[b'path']})
        else:
            self.length = self.info[b'length']

        self.last_piece_length = self.length - (self.piece_length * (self.num_pieces - 1))

        # create list of Piece objects
        self.pieces = []
        
        # SHA1 hashes of length 20 for each piece
        for i in range(0, len(self.info[b'pieces']), 20):
            if i + 20 >= len(self.info[b'pieces']):
                is_final_piece = True
                piece_length = self.last_piece_length
            else:
                is_final_piece = False
                piece_length = self.piece_length

            piece_hash = self.info[b'pieces'][i:i+20]
            index = i // 20

            self.pieces.append(Piece(index, piece_hash, piece_length, is_final_piece))