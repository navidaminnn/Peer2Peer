import utils.bencoding as bencoding
from tracker import Tracker
from metainfo import MetaInfo
from collections import OrderedDict
from connection import PeerProtocol, PeerFactory
from models.piece_status import PieceStatus
from models.file_writer import FileWriter
from models.piece import Piece
from twisted.internet.endpoints import TCP4ClientEndpoint, TCP4ServerEndpoint
from twisted.internet import reactor
from twisted.internet.endpoints import connectProtocol
import os

def start_server(tracker: Tracker, meta_info: MetaInfo, piece_status: PieceStatus, file_writer: FileWriter):
    endpoint = TCP4ServerEndpoint(reactor, 8000)
    factory = PeerFactory(tracker.peers, meta_info.info_hash, tracker.peer_id, piece_status, file_writer)
    endpoint.listen(factory)

    for peer in tracker.peers:
        client = TCP4ClientEndpoint(reactor, peer.host, int(peer.port))
        d = connectProtocol(client, PeerProtocol(factory, peer))
        d.addCallback(connected_protocol)
        d.addErrback(error_handle)

def connected_protocol(protocol):
    protocol.send_handshake()

def error_handle(error):
    pass

if __name__ == "__main__":
    meta_info = MetaInfo(file_path)
    meta_info.parse_file()

    tracker = Tracker(meta_info)
    tracker.fetch_peers()
    
    piece_status = PieceStatus(tracker.peers, meta_info)

    file_writer = FileWriter(meta_info, piece_status)

    print(f"Number of pieces: {meta_info.num_pieces}")
    print(f"Number of peers: {len(tracker.peers)}")
    print(f"Piece length: {meta_info.piece_length}")

    start_server(tracker, meta_info, piece_status, file_writer)

    reactor.run()
