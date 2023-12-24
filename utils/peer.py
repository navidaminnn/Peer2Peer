class Peer:
    '''
    simple class for Peer objects
    '''

    def __init__(self, host: str, port: str):
        self.host = host
        self.port = port

        self.info_hash = None
        self.peer_id = None