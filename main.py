import utils.bencoding as bencoding
from tracker import Tracker
from metainfo import MetaInfo
from collections import OrderedDict
from peer import PeerConnection
import asyncio

def start_server(tracker: Tracker, meta_info: MetaInfo):
    peer_conn = PeerConnection(tracker.peers[0], meta_info.info_hash, tracker.peer_id)

    asyncio.run(peer_conn)

if __name__ == "__main__":
    file_path = ""
    meta_info = MetaInfo(file_path)
    meta_info.parse_file()

    tracker = Tracker(meta_info)
    tracker.fetch_peers()

    start_server(tracker, meta_info)
