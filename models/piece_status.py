from models.peer import Peer
from metainfo import MetaInfo
from models.piece import Piece

class PieceStatus:
    '''
    keeps track of the status of all pieces and 
    which peers own which pieces
    '''

    def __init__(self, peers: list, meta_info: MetaInfo):
        self.meta_info = meta_info
        self.pieces = meta_info.pieces
        self.peers = peers
        self.num_pieces = meta_info.num_pieces

        self.piece_length = meta_info.piece_length
        self.last_piece_length = meta_info.last_piece_length
        self.file_size = meta_info.length

        self.owned_pieces = []
        self.missing_pieces = self.pieces.copy()
        self.ongoing_pieces = []

        self.peers_own = {peer : [] for peer in self.peers}

    def update_peers_own(self, index: int, peer: Peer):
        '''
        update peers that own missing pieces using index of piece
        '''

        piece = self.pieces[index]

        self.peers_own[peer].append(piece)

    def update_completed_pieces(self, index: int):
        self.ongoing_pieces.remove(self.pieces[index])
        self.owned_pieces.append(self.pieces[index])

    def update_ongoing_pieces(self, index: int):
        self.missing_pieces.remove(self.pieces[index])
        self.ongoing_pieces.append(self.pieces[index])
        
    # def choose_next_piece(self, peer: Peer) -> Piece | None:
    #     '''
    #     picks a random piece that's missing & owned by the peer

    #     TODO: implement a rarest-first algorithm to make torrent more effective
    #     '''

    #     missing_set = set(self.missing_pieces)
    #     peer_set = set(self.peers_own[peer])

    #     desired_pieces = missing_set.intersection(peer_set)

    #     if len(desired_pieces) == 0:
    #         return None

    #     return desired_pieces.pop()
        
    import bitstring

    def choose_next_piece(self, bitfield: bitstring.BitArray) -> Piece | None:
        desired_pieces = {piece for bit, piece in zip(bitfield, self.missing_pieces) if bit}

        if len(desired_pieces) == 0:
            return None
        
        return desired_pieces.pop()
    
    def get_piece_index(self, piece: Piece) -> int:
        return self.pieces.index(piece)
    
    def download_completed(self) -> bool:
        return (len(self.missing_pieces) == 0 and
                len(self.ongoing_pieces) == 0 and
                len(self.owned_pieces) == len(self.pieces))
