import requests
from collections import OrderedDict

class HttpRequest:
    def fetch_response(self, request_param: dict, announce: tuple):
        '''
        docs for understanding url formatting
        https://www.rfc-editor.org/rfc/rfc1808.html#section-2.1
        '''
        
        url = announce.scheme + '://' + announce.netloc + announce.path

        response = requests.get(url, params=request_param)
        
        return response.content
    
    def parse_response(self, response: OrderedDict):
        '''
        parse through the response and 
        return all important information

        docs for understanding response
        https://wiki.theory.org/BitTorrentSpecification#Tracker_Response
        '''

        '''
        list of information from response
        - complete
        - incomplete
        - interval
        - peers
            - ip
            - peer id
            - port
        '''

        self.interval = response[b'interval']
        

