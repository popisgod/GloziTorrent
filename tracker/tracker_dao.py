
from fastapi import HTTPException
import json
from typing import List, Dict, Any, AnyStr
from collections import UserDict
from pydantic import BaseModel
import logging
from dataclasses import dataclass
from pymongo import MongoClient


logging.basicConfig(filename='tracker.log', level=logging.INFO, filemode='w', format='%(asctime)s - %(message)s',datefmt='%d-%b-%y %H:%M:%S')

# deprecated class
# class TrackerRequestRegister(BaseModel):
#         info_hash : str
#         peer : dict

@dataclass
class Peer():
    peer_id : str
    ip : str
    port : int
    downloaded : str 
    uploaded : str
    left : str
    event : str

@dataclass
class TrackerFile():
    info_hash : str
    peers : List[Peer]
    

class Dao:
    def __init__(self, dbconnection : MongoClient) -> None:
        self.dbconnection = dbconnection['tracker_files']
        
    
    def update_tracker_files(self, info_hash : str, peer : Peer) -> List[Peer]:
        '''updates tracker file peer list. returns 404, if file wasn't registered yet'''
        if self.tracker_files.get(info_hash):
            file : TrackerFile = self.tracker_files[info_hash]
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
            self.tracker_files[info_hash] = TrackerFile(info_hash=info_hash,
                                                        peers=[peer,])
            logging.info(f'peer {peer.peer_id} has announced of a new tracker file {info_hash}')
            return [peer,]
        
            
    # deprecated method 
    # def add_tracker_file(self, info_hash : str, peer : Peer) -> None:
    #     '''creates a new tracker file and appends it to the tracker file list'''
    #     logging.info(f'current tracker files {self.tracker_files}')
    #     if self.tracker_files.get(info_hash) is None:
    #         new_file = TrackerFile(info_hash, [peer,])
    #         self.tracker_files[info_hash] = new_file
    #         logging.info(f'new tracker file created {info_hash}')
            
    #         return TrackerResponse(tracker_file=new_file.to_dict())
    #     raise HTTPException(status_code=404 , detail="Tracker file already exists")
    

if __name__=='__main__':
    pass
    
