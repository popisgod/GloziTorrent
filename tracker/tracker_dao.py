
from fastapi import HTTPException
import json
from typing import List, Dict, Any
from collections import UserDict
from pydantic import BaseModel


class Peer(UserDict):
    
    @classmethod
    def from_dict(cls, peer_dict: dict) -> 'Peer':
        peer_id = peer_dict.get('peer_id', '')
        ip = peer_dict.get('ip', '')
        port = peer_dict.get('port', 0)
        
        return cls(peer_id, ip, port)
    
    def to_dict(self) -> dict:
        return self.data
        
    def __init__(self, id : str, ip : str, port : int) -> None:
        super().__init__()
        self.data = {
            'peer_id' : id,
            'ip' : id,
            'port' : port,
        }

    def to_json(self) -> str:
        return json.dumps(self.data)  



class TrackerFile(UserDict):
    def __init__(self, info_hash : str, peers : List[Peer]) -> None:
        super().__init__()
        self.data = {
            'info_hash' : info_hash,
            'peers' : peers
        }    
        
    def to_dict(self) -> dict:
        return self.data
    
    def to_json(self) -> str:
        return json.dumps(self.data)        



class Dao:
    def __init__(self) -> None:
        self.tracker_files = {}
    
    def update_tracker_file(self, info_hash : str, peer : Peer) -> List[Peer]:
        '''updates tracker file peer list. returns 404, if file wasn't registered yet'''
        if self.tracker_files.get(info_hash):
            file : TrackerFile = self.tracker_files[info_hash]
            peers : List[Peer] = file['peers'] 
            
            for index, existing_peer in enumerate(peers):
                if existing_peer['id'] == peer['id']:
                    peers[index] = peer
                    break
            else:
                peers.append(peer)
                return file.to_dict()
        else: 
            raise HTTPException(status_code=404, detail="Tracker file doesn't exist")
             
            
    def add_tracker_file(self, info_hash : str, peer : Peer) -> None:
        '''creates a new tracker file and appends it to the tracker file list'''
        if self.tracker_files.get(info_hash) is None:
            new_file = TrackerFile(info_hash, [peer,])
            self.tracker_files[info_hash] = new_file
            return new_file.to_dict()
        raise HTTPException(status_code=409 , detail="Tracker file already exists")
    
class TrackerRequest(BaseModel):
    info_hash : str
    peer : Dict[str, Any]

if __name__=='__main__':
    pass
    
  