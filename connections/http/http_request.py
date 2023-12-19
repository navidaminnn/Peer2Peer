import requests
from collections import OrderedDict
from urllib.parse import urlencode
import ipaddress

class HttpRequest:
    def format_request(self, request_param: dict, announce: tuple):
        '''
        docs for understanding url formatting
        https://www.rfc-editor.org/rfc/rfc1808.html#section-2.1
        '''
        
        url = announce.scheme + '://' + announce.netloc + announce.path + '?'

        response = requests.get(url, params=request_param)
        
        return response.content
    
    def parse_request(self, response):
        '''
        parse through the response and 
        return all important information

        docs for understanding response
        https://wiki.theory.org/BitTorrentSpecification#Tracker_Response

        based on testing, seems like if dict contains 'peers'
        it's compact (or maybe IPv4?) and if it contains 'peers6'
        it's IPv6 instead
        '''

        # assume it's compact in this case - change if it can be IPv4
        if b'peers' in response and type(bytes):
            peers = response[b'peers']
            pass
        else:
            #TODO: add IPv6 compatability
            raise TypeError('Not in compact mode - cannot be parsed')

