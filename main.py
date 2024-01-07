import utils.bencoding as bencoding
from tracker import Tracker
from metainfo import MetaInfo
from connection import PeerProtocol, PeerFactory
from models.piece import Piece
from twisted.internet.endpoints import TCP4ClientEndpoint, TCP4ServerEndpoint
from twisted.internet import reactor
from twisted.internet.endpoints import connectProtocol

def start_server(tracker: Tracker, meta_info: MetaInfo):
    endpoint = TCP4ServerEndpoint(reactor, 8000)
    factory = PeerFactory(tracker.peers, meta_info, tracker.peer_id)
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

    print(f"Number of pieces: {meta_info.num_pieces}")
    print(f"Number of peers: {len(tracker.peers)}")
    print(f"Piece length: {meta_info.piece_length}")
    print("Total # of bytes: %d" % meta_info.length)

    start_server(tracker, meta_info)

    reactor.run()