from utils.peer import Peer
from metainfo import MetaInfo

class PieceStatus:
    '''
    keeps track of the status of all pieces and 
    which peers own which pieces
    '''

    def __init__(self, peers: list, meta_info: MetaInfo):
        self.meta_info = meta_info
        self.pieces = meta_info.pieces
        self.peers = peers

        self.piece_length = meta_info.piece_length
        self.last_piece_length = meta_info.last_piece_length
        self.file_size = meta_info.length

        self.owned_pieces = []
        self.missing_pieces = self.pieces
        self.ongoing_pieces = []

        self.peers_own = {peer : [] for peer in self.peers}

    def update_peers_own(self, index: int, peer: Peer):
        '''
        update which peers own which pieces using index of piece
        '''

        self.peers_own[peer].append(self.pieces[index])

    def update_completed_pieces(self, index: int):
        self.owned_pieces.append(self.pieces[index])
        self.missing_pieces.remove(self.pieces[index])
        self.ongoing_pieces.remove(self.pieces[index])

    def update_ongoing_pieces(self, index: int):
        self.ongoing_pieces.append(self.pieces[index])
    
    # def bytes_downloaded(self) -> int:
    #     return len(self.owned_pieces) * self.piece_length
    
    # def bytes_remaining(self) -> int:
    #     return self.file_size - len(self.owned_pieces) * self.piece_length
