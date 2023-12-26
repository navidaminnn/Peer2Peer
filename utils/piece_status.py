from utils.peer import Peer
from metainfo import MetaInfo
from piece import Piece

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
        
    def choose_next_piece(self, peer: Peer):
        '''
        picks a random piece that's missing & owned by the peer

        TODO: implement a rarest-first algorithm to make torrent more effective
        '''

        missing_set = set(self.missing_pieces)
        peer_set = set(self.peers_own[peer])

        chosen_piece: Piece = missing_set.intersection(peer_set).pop()

        return chosen_piece
    
    def get_piece_index(self, piece: Piece):
        return self.pieces.index(piece)
