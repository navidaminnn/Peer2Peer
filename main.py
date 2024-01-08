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

def print_info(meta_info: MetaInfo, tracker: Tracker):
    print("\nTorrent File Name: %s" % meta_info.file_name)
    print("Number of Pieces: %d" % meta_info.num_pieces)
    print("Piece Length: %d" % meta_info.piece_length)
    print("Last Piece Length: %d" % meta_info.last_piece_length)
    print("Total # of Bytes: %d" % meta_info.length)
    print("Number of Peers: %d" % len(tracker.peers))

    print("\nFile names and their sizes:")
    if meta_info.multi_files:
        for file in meta_info.files:
            print(" - '%s' (%d bytes)" % (file['path'][len(file['path']) - 1], file['length']))
    else:
        print(" - '%s' (%d bytes)" % (meta_info.name, meta_info.length))

if __name__ == "__main__":
    print("To use the Peer2Peer client, please type in the name of your torrent file!")
    print("(you're not required to type the '.torrent' part)")

    torrent_file = input().strip()

    if not torrent_file.endswith('.torrent'):
        torrent_file += '.torrent'

    meta_info = MetaInfo(torrent_file)
    meta_info.parse_file()

    tracker = Tracker(meta_info)
    tracker.fetch_peers()

    print_info(meta_info, tracker)

    start_server(tracker, meta_info)

    reactor.run()