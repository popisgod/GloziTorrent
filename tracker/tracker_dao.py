from __future__ import annotations
from typing import List, Dict, Any, Union
from pydantic import BaseModel
import logging
from pymongo import MongoClient

# logging configuration 
logging.basicConfig(filename='tracker.log', level=logging.INFO, filemode='w', format='%(asctime)s - %(message)s',datefmt='%d-%b-%y %H:%M:%S')


class Peer(BaseModel):
    peer_id: str
    ip: str
    port: int
    downloaded: str
    uploaded: str
    left: str
    event: str
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Peer:
        '''deprecated method, use cls(**data) instead'''
        return cls(**data)
    
    def to_dict(self) -> Dict[str, Any]:
        '''deprecated method, use self.dict() instead'''
        return self.dict()


class TrackerFile(BaseModel):
    info_hash : str
    peers : List[Peer]
    
    @classmethod
    def from_dict(cls, data : Dict[str, Any]) -> TrackerFile:
        info_hash = str(data.get('info_hash', ' '))
        peers_data = list(data.get('peers', []))
        peers = [Peer(**peer) for peer in peers_data]
    
        return cls(info_hash=info_hash, peers=peers)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'info_hash' : self.info_hash,
            'peers' : [peer.to_dict() for peer in self.peers]
        } 
      

class Dao:
    def __init__(self, dbconnection : MongoClient) -> None:
        self.dbconnection = dbconnection['tracker']
        self.dbtable =  self.dbconnection['tracker_files']
        

    def update_tracker_files(self, info_hash : str, peer : Peer) -> List[Peer]:
        '''updates tracker file peer list. returns 404, if file wasn't registered yet'''
        info_hash_query = {'info_hash' : info_hash}
        result = self.dbtable.find_one(info_hash_query)
        if result:
            file : TrackerFile = TrackerFile.from_dict(result)
            peers : List[Peer] = file.peers
            
            for index, existing_peer in enumerate(peers):
                if existing_peer.peer_id == peer.peer_id:
                    logging.info(f'peer {peer.peer_id} has been updated : tracker_file {info_hash}')
                    peers[index] = peer
                    break
            else:
                peers.append(peer)
                logging.info(f'peer {peer.peer_id} has joined tracker file {info_hash}')
            return peers
            
        else: 
            self.dbtable.insert_one(TrackerFile(info_hash=info_hash, peers=[peer,]).to_dict())
            logging.info(f'peer {peer.peer_id} has announced of a new tracker file {info_hash}')
            return [peer,]
        
        
if __name__=='__main__':
    pass
    
