# Standard library imports
import requests 
import socket 
import pickle 
import json
import os 
import hashlib
import pathlib
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
import shutil

# Third party imports 


# Local application imports
from utils import networking_utils 


BUFSIZE = 256000
TORRENT_FILES_DIR = '.torrent'

@dataclass
class Address:
    ip : str
    port : int

@dataclass
class Message: 
    msg : str
    data : Any

@dataclass
class FilePart:
    file_name : str
    part_hash : str
    data : bytes
    part_num : int | None = None
    


class Peer: 
    def __init__(self) -> None:
        # tracker holding information about peers 
        self.tracker = 'http://10.100.102.3:5000/'
        self.port = networking_utils.get_open_port()
        self.ip = networking_utils.get_host_ip()
        self.peer_id = get_id()
        self.stopped = []

        # socket for connecting to peers 
        self.socket = socket.socket(
            socket.AF_INET, 
            socket.SOCK_STREAM
        )
        
        # server socket listening to peer requests 
        self.server = PeerServer(
            port=self.port,
            peer_id=self.peer_id
        )
        
        
        for torrent_name in os.listdir(TORRENT_FILES_DIR):
            with open(os.path.join(TORRENT_FILES_DIR, torrent_name), 'r') as file:
                data = json.load(file)
            self.announce(data['info_hash'], 'paused')        


    def announce(self, info_hash : str, event : str) -> None | List[dict[str, str]]:
        announce_url = self.tracker + 'announce/'

        
        params = {
            'info_hash' : info_hash,
            'peer_id' : self.peer_id,
            'ip' : self.ip,
            'port' : self.port,
            'downloaded' : '0',
            'uploaded' : '0',
            'left' : '0',
            'event' : event
        } 
        
        announce_res = requests.get(announce_url, params=params)
        if announce_res.status_code != 200:
            print('api does not respond')

        print(announce_res.json())
        return announce_res.json()
        
        
    def create_torrent_file(self,file_path : str) -> str: 
        """

        Returns:
            str: file path of the torrent file 
        """
        chunk_size = BUFSIZE // 2
        path = pathlib.Path(file_path)
        os.makedirs(path.stem, exist_ok=True)

        

        parts = {}
        part_order = 0
        with open(file_path, 'rb') as file:
            file_hash = hashlib.sha256()
            while True:
                chunk = file.read(chunk_size)
                if not chunk:
                    break
                file_hash.update(chunk)

                chunk_hash = hashlib.sha256(chunk).hexdigest()
                chunk_file_path = os.path.join(path.stem, f"{chunk_hash}.bin")
                with open(chunk_file_path, 'wb') as chunk_file:
                    chunk_file.write(chunk)

                parts[part_order] = chunk_hash
                part_order += 1
            
        info = {
                'length' : os.path.getsize(file_path),
                'path' : '', 
                'name' : path.name,
                'piece length' : chunk_size,   
                'pieces' : parts,
                'file_hash' : file_hash.hexdigest(), 
                
            }
        info_hash = hashlib.sha256(bytes(json.dumps(info), 'utf-8')).hexdigest()
        torrent_dict = {
            'announce' : self.tracker,
            'info' : info, 
            'info_hash' : info_hash
            
        }
        
        if os.path.exists(info_hash): 
            shutil.rmtree(info_hash)
        os.rename(path.stem, info_hash)
        
        
        torrent_path = os.path.join(TORRENT_FILES_DIR, path.stem + '.torrent')
        with open(torrent_path, 'w') as file:
            json.dump(torrent_dict, file)
        
        return torrent_path
    
    
    def get_torrent_file(self, info_hash : str, peers : List[Address]) -> Dict[str, Any] | None:
        # connect to peers 
        for address in peers: 
            try: 
                self.socket.connect((address.ip, address.port))
                
                msg = Message('.torrent', info_hash)
                self.socket.send(pickle.dumps(msg))

                recv_msg : Message = pickle.loads(self.socket.recv(BUFSIZE))
                
                if recv_msg.msg == '.torrent': 
                    if recv_msg.data is not None:
                        return recv_msg.data
                
            except socket.error as e: 
                print(f"Error connecting to {address.ip}:{address.port}: {e}")
        print('file wasn not found')
   
    
    def download_file(self, info_hash : str) -> None:
        peers = self.announce(info_hash,'started')
        if peers is None:
            print('File does not exist')
            return
        if len(peers) == 1:
            print('No peers hold the file')
            return 
        
        addresss_list = []
        for peer in peers:
            addresss_list.append(Address(peer['ip'], int(peer['port'])))
        torrent_file = self.get_torrent_file(info_hash, addresss_list) 
        if torrent_file is None:
            print('File does not exist')
            return    
        with open(os.path.join(TORRENT_FILES_DIR, torrent_file['name']), 'w') as file:
            json.dump(torrent_file, file)
            
        file_path = torrent_file['name'].split('.')[0]
        
        os.makedirs(file_path,exist_ok=True)
        parts_missing = list(torrent_file['info']['parts'].values())
        for part in os.listdir(file_path): 
            if part in parts_missing:
                parts_missing.remove(part)
        
        parts_per_peer = self.get_file_parts_availablity(info_hash, addresss_list)
        
        while parts_missing: 
            for address in addresss_list:
                parts_hash = parts_per_peer.get(address, None)
                if parts_hash is not None:
                    try: 
                        for part_hash in parts_hash: 
                            if part_hash in parts_missing:
                                self.socket.connect((address.ip, address.port))
                                
                                msg = Message('part', part_hash)
                                self.socket.send(pickle.dumps(msg))
                                
                                part = pickle.loads(self.socket.recv(BUFSIZE))
                                if hashlib.sha256(part).hexdigest() == part_hash:
                                    with open(os.path.join(file_path, part_hash + '.bin'), 'wb') as file:
                                        file.write(part)
                                    parts_missing.remove(part_hash)    
                                parts_hash.remove(part_hash)
                                break
                    except socket.error as e: 
                        print(f"Error connecting to {address.ip}:{address.port}: {e}")    
            if all(element == [] for element in list(parts_per_peer.values()))
                print('peers miss a part, file is not downloadable')
                return 
          
            
    def get_file_parts_availablity(self, info_hash : str, peers : List[Address]) -> Dict[Address, List[str]]:
        
        parts_per_peer = {}
        for address in peers:
            try:
                self.socket.connect((address.ip, address.port))

                msg = Message('parts_available', info_hash)
                self.socket.send(pickle.dumps(msg))
                
                data = pickle.loads(self.socket.recv(BUFSIZE))
                parts_per_peer[address] = data

            except socket.error as e: 
                print(f"Error connecting to {address.ip}:{address.port}: {e}")
        return parts_per_peer
        
            
    @staticmethod
    def torrent_file_exists(info_hash : str) -> Dict[str, Any] | None:
        for filename in os.listdir(TORRENT_FILES_DIR):
            # open file and read its contents 
            file_path = os.path.join(TORRENT_FILES_DIR, filename)
            with open(file_path, 'r') as file:
                data = json.load(file)
            
            if data['info_hash'] == info_hash:
                return data
        return None             


    @staticmethod
    def file_part_exists(file_part : FilePart) -> FilePart | None:
        part_path = os.path.join(file_part.file_name, file_part.part_hash + '.bin')
        if os.path.exists(part_path):
            with open(part_path, 'rb') as file:
                file_part.data = file.read()
            return file_part
        return None


    @staticmethod
    def file_parts_available(info_hash : str) -> List[str]:
        hashes = []
        if os.path.exists(info_hash): 
            for filepart in os.listdir(info_hash):
                hash = filepart.split('.')[0]
                hashes.append(hash)
        return hashes

class PeerServer(socket.socket):
    def __init__(self, port : int, peer_id : str) -> None:
        super().__init__(socket.AF_INET, socket.SOCK_STREAM)
    


def get_id() -> str:
    with open('settings.json', 'r') as file:
        data = json.load(file)
    return data['UUID']
        
    
if __name__=='__main__':
    
    # ------- tests -------
    
    if not os.path.exists(TORRENT_FILES_DIR):
        os.makedirs(TORRENT_FILES_DIR, exist_ok=True)

    
    # creating a torrent file 
    peer = Peer()
    torrent_path = peer.create_torrent_file(r"C:\Users\Ron\Downloads\Web scraping- example.pptx")
    
    with open(torrent_path, 'r') as f: 
        data = json.load(f)
    info_hash = data['info_hash']
    
    # check what file parts are available 
    torrent_data = Peer.torrent_file_exists(info_hash)
 
    peer.announce(data['info_hash'], '')
    
    if torrent_data:
        file_parts = Peer.file_parts_available(torrent_data['info_hash']) 
    
    