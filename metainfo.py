import utils.bencoding as bencoding
from hashlib import sha1

class MetaInfo:
    def __init__(self, file_name):
        self.file_name = file_name
        self.multi_files = False

        with open(file_name, 'rb') as file:
            self.file_contents = bencoding.Decoder(file.read()).decode()

        print(self.file_contents)

    #TODO: info dict needs to be encoded as SHA1 hash?
    def parse_file(self):
        '''
        docs for understanding file structure
        https://wiki.theory.org/BitTorrentSpecification#Metainfo_File_Structure
        '''

        # first parse all the info that is consistent whether it's single file or multi file
        self.announce_url = self.file_contents[b'announce']
        self.info = self.file_contents[b'info']
        # info hash will be used for tracker later on
        self.info_hash = sha1(bencoding.Encoder().encode(self.info)).digest()

        # check for all optional contents
        if b'announce-list' in self.file_contents:
            self.announce_list = self.file_contents[b'announce-list']

        if b'creation date' in self.file_contents:
            self.creation_date = self.file_contents[b'creation date']

        if b'encoding' in self.file_contents:
            self.encoding = self.file_contents[b'encoding']

        # now check for everything in info dict
        self.piece_length = self.info[b'piece length']
        self.pieces = self.info[b'pieces']
        self.piece_num = len(self.pieces) // 20
        self.name = self.info[b'name']

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

            self.last_piece_length = self.length - (self.piece_length * (self.piece_num - 1))
        else:
            self.length = self.info[b'length']
            self.last_piece_length = self.length
        


        
        