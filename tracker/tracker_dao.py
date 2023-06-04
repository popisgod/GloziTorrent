from __future__ import annotations
from typing import List, Dict, Any, Literal, Annotated, Union
from pydantic import BaseModel
from fastapi import Depends
import logging
from pymongo import MongoClient
import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError
import config 
from passlib.context import CryptContext
import datetime


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class Peer(BaseModel):
    peer_id: str
    ip: str
    port: int
    downloaded: str
    uploaded: str
    left: str
    event: Literal['','started','completed','stopped']


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
            'peers' : [peer.dict() for peer in self.peers]
        } 



class TrackerDao:
    def __init__(self, dbconnection : MongoClient, password : str) -> None:
        """_summary_

        Args:
            dbconnection (MongoClient): _description_
            password (str): _description_
        """
        self.mongo_client = dbconnection
        self.database = self.mongo_client['tracker']
        self.tracker_files_table =  self.database['tracker_files']
        self.authentication_table = self.database['authentication']
        
    def update_tracker_files(self, info_hash : str, 
                             peer : Annotated[Peer, Depends(Peer)], 
                             compact_mode : bool, 
                             no_peer_id : bool, 
                             numwant : int | None,
                             ) -> List[Peer]:
        """updates the tracker files or creates a new file per peer requets.

        Args:
            info_hash (str): the info_hash of the specified .torrent file 
            peer (Peer): peer object containing information about the peer and its file status

        Returns:
            List[Peer]: a list of all peers taking part in the .torrent file by info_hash
        """

        
        info_hash_query = {'info_hash' : info_hash}
        result = self.tracker_files_table.find_one(info_hash_query)
        if result:
            file : TrackerFile = TrackerFile.from_dict(result)
            peers : List[Peer] = file.peers
            
            for index, existing_peer in enumerate(peers):
                if existing_peer.peer_id == peer.peer_id:
                    logging.info(f'peer {peer.peer_id} has been updated : tracker_file {info_hash}')
                    peers[index] = peer
                    self.tracker_files_table.update_one(info_hash_query, {'$set' : file.dict()})
                    break
            else:
                peers.append(peer)
                self.tracker_files_table.update_one(info_hash_query, {'$set' : file.dict()})
                logging.info(f'peer {peer.peer_id} has joined tracker file {info_hash}')
            return peers
            
        else: 
            new_file = TrackerFile(info_hash=info_hash, peers=[peer,])
            self.tracker_files_table.insert_one(new_file.to_dict())
            logging.info(f'peer {peer.peer_id} has announced of a new tracker file {info_hash}')
            return [peer,]
    
    def get_all_tracker_files(self) -> List[TrackerFile]:
        """returns all of the tracker files

        Returns:
            List[TrackerFile]: a list of all of the tracker files stored on the database 
        """
        result: List[Dict[str, Any]] = list(self.tracker_files_table.find())
        logging.warning(result)
        return [TrackerFile.from_dict(tracker_file) for tracker_file in result]
    
    def login_admin(self, username : str, password : str, ip : str) -> Dict[str, str] | None:
        """checks if the username and password are valid and generates a temporary token

        Args:
            password (str): admin password
            username (str): admin username 

        Returns:
            Dict[str, str] | None: an authentication token 
        """
        authenticate_hash_query = {'username' : username, 'scope' : 'admin'}
        result = self.authentication_table.find_one(authenticate_hash_query)
        if result: 
            if verify_password(password ,result['hashed_password']):
                return {"access_token": self.generate_token('admin', ip, config.ACCESS_TOKEN_EXPIRE_SECONDS), "token_type": "Bearer"}
        return None
        
    def generate_token(self, scope : str, ip : str, expiration : int = config.ACCESS_TOKEN_EXPIRE_SECONDS) -> str: 
        """ generates an authentication token for the specified scope with a time limit 

        Args:
            scope (str): _description_
            time_limit (int): time limit of the token in seconds 
            ip (str): ip of the user will be used as salt 
        Returns:
            str: _description_
        """
        data = {
            'ip' : ip,
            'scope' : scope,
            'exp' : datetime.datetime.now()
                       + datetime.timedelta(seconds=expiration)

        }
        token = jwt.encode(payload=data, 
                           key=config.SECRET_KEY, 
                           algorithm="HS256")
        return token
    
    def authenticate_token(self, token : str, scope : str, ip : str) -> Literal["TOKEN_EXPIRED", "BAD_TOKEN","TOKEN_VALID"]: 
        """authenticate received token 

        Args:
            token (str): _description_

        Returns:
            bool: _description_
        """     
        
        try: 
            data = jwt.decode(token,
                              key=config.SECRET_KEY,
                              leeway=datetime.timedelta(seconds=10), 
                              algorithms=["HS256"])

            if data['ip'] == ip:
                if data['scope'] == scope:
                    return "TOKEN_VALID"
                
            return "BAD_TOKEN"
        except ExpiredSignatureError:
            return "TOKEN_EXPIRED"
        except InvalidTokenError:
            return "BAD_TOKEN"
    
    def create_user(self, username : str, password : str, scope : str) -> None:
        """creates a new admin user and sets its username and password

        Args:
            username (str): the username of the admin
            password (str): the password of the user 
            scope (str): the scope of the newly created user 
        """
        authentication_hash_query = {'hashed_password' : hash_password(password), 
                                     'username' : username,
                                     'scope' : scope}
        self.authentication_table.insert_one(authentication_hash_query)


def hash_password(password : str) -> str: 
    """ takes in a password and returns the hashed password 

    Args:
        password (str): a password of any type

    Returns:
        str: the hashed password 
    """
    return pwd_context.hash(password)

def verify_password(password_to_verify : str, hashed_password : str) -> bool:
    """_summary_

    Args:
        password_to_verify (str): _description_
        hashed_password (str): _description_

    Returns:
        bool: _description_
    """
    return pwd_context.verify(password_to_verify, hashed_password)






if __name__=='__main__':
    pass
    
