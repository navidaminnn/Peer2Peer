# Peer2Peer
torrenting client following the BitTorrent protocol - allows users to utilize peer-to-peer connections to download pieces of a file!

![peer2peer](https://github.com/navidaminnn/Peer2Peer/assets/135196056/a2c4817c-61e0-4273-91f4-cba7b9d64c13)

## Built With
* Python
* Twisted
* Requests

## Features
* Downloading torrent files
* Allows for quick, concurrent peer-to-peer TCP connections
* Single file torrents
* Multi file torrents
* Supports UDP and HTTP(S) trackers
* Both compact-mode and dictionary-mode peer lists work
* Supports both IPv4 and IPv6 peer IP addresses

## Requirements
* Python 3.11+
* All of the libraries/modules in the requirements.txt

## Installation / Setup
  1. Clone the repository
  2. Install all required libraries/modules for the client by doing ```pip install -r requirements.txt```
  3. Download the torrent file you'd like
  4. Drag the torrent file into the repository's root folder
  5. Run the program using ```python main.py```
  6. Follow the instructions in the command line
  7. The download will now begin!

## Future Goals
* Implementing a more efficient piece-choosing algorithm (rarest first?)

## References
* [Official BitTorrent Protocols](https://www.bittorrent.org/beps/bep_0000.html) - provides all the necessary information given that it's the official docs
* [BitTorrentSpecification Wiki](https://wiki.theory.org/BitTorrentSpecification) - provides more insight and detail into various parts of the process and also gives different perspectives/takes on design choices
