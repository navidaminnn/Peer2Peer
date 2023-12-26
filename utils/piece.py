import math

class Piece:
    BLOCK_SIZE = 2**14

    def __init__(self, piece_hash: bytes, length: int, is_final: bool):
        self.hash = piece_hash
        self.length = length
        self.is_final = is_final # TODO: is this even needed? already accounted when instantiating object

        self.num_blocks = math.ceil(self.length / self.BLOCK_SIZE)

        self.final_block_size = self.length % self.BLOCK_SIZE

        # index of next block to download
        self.block_to_download = 0

    def get_block_size(self):
        '''
        return appropriate block size depending on
        if it's the final block in the piece or not
        '''

        if self.block_to_download == self.num_blocks - 1:
            return self.final_block_size

        return self.BLOCK_SIZE