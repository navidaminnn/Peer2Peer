import math

class Piece:
    BLOCK_SIZE = 2**14

    def __init__(self, piece_hash: bytes, length: int, is_final: bool):
        self.hash = piece_hash
        self.length = length
        self.is_final = is_final

        self.num_blocks = math.ceil(self.length / self.BLOCK_SIZE)
        self.num_blocks_needed = self.num_blocks

        self.final_block_size = self.length % self.BLOCK_SIZE