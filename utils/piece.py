import math

class Piece:
    BLOCK_SIZE = 2**14

    def __init__(self, piece_hash: bytes, length: int, is_final: bool):
        self.hash = piece_hash
        self.length = length
        self.is_final = is_final

        self.num_blocks = math.ceil(self.length / self.BLOCK_SIZE)

        self.final_block_size = self.length % self.BLOCK_SIZE

        # index of next block to download
        self.block_index = 0

    def get_block_size(self):
        '''
        return appropriate block size depending on
        if it's the final block in the piece or not
        '''

        if self.block_index == self.num_blocks - 1:
            return self.final_block_size

        return self.BLOCK_SIZE
    
    def is_equal_hash(self, hash: bytes):
        return hash == self.hash
    
    def on_final_block(self):
        return self.block_index == self.num_blocks - 1
    
    def is_downloaded(self):
        return self.block_index >= self.num_blocks
    
    def get_byte_offset(self):
        return self.block_index * self.BLOCK_SIZE