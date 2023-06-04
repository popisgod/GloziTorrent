from __future__ import annotations
from typing import List, Dict, Any, Literal, Annotated, Union
from pydantic import BaseModel, validator, root_validator
from fastapi import Depends
import logging
from pymongo import MongoClient
import jwt
from itsdangerous import TimestampSigner, URLSafeTimedSerializer as Serializer
from itsdangerous.exc import BadSignature, SignatureExpired
import config 
from passlib.context import CryptContext
from datetime import datetime, timedelta


class Peer(BaseModel):
    peer_id: str
    ip: str
    port: int
    downloaded: str
    uploaded: str
    left: str
    event: Literal['','started','completed','stopped']


class Token(BaseModel):
    token: str  
    expiration_time : int = 3600 

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



class Dao:
    def __init__(self, dbconnection : MongoClient, password : str) -> None:
        """_summary_

        Args:
            dbconnection (MongoClient): _description_
            password (str): _description_
        """
        self.dbconnection = dbconnection['tracker']
        self.tracker_files_table =  self.dbconnection['tracker_files']
        self.authentication_table = self.dbconnection['authentication']
        
    def update_tracker_files(self, info_hash : str, 
                             peer : Annotated[Peer | dict, Depends(Peer)], #TODO: why doesn't it enforce conversion????
                             compact_mode : bool, no_peer_id : bool, 
                             numwant : int | None,
                             ) -> List[Peer]:
        """updates the tracker files or creates a new file per peer requets.

        Args:
            info_hash (str): the info_hash of the specified .torrent file 
            peer (Peer): peer object containing information about the peer and its file status

        Returns:
            List[Peer]: a list of all peers taking part in the .torrent file by info_hash
        """
        if isinstance(peer,dict): #TODO: fix this buggg, it doesn't enfore type and passes it as a dict 
            peer = Peer(**peer)
        
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
        authenticate_hash_query = {'hashed_password' : hash_password(password), 'username' : username, 'scope' : 'admin'}
        result = self.authentication_table.find_one(authenticate_hash_query)
        if result: 
            return {"access_token": self.generate_token('admin', ip), "token_type": "bearer"}
        
        
    def generate_token(self, scope : str, ip : str) -> str: 
        """ generates an authentication token for the specified scope with a time limit 

        Args:
            scope (str): _description_
            time_limit (int): time limit of the token in seconds 
            ip (str): ip of the user will be used as salt 
        Returns:
            str: _description_
        """
        serializer = Serializer(config.SECRET_KEY)
        token = serializer.dumps({'ip' : ip, 'scope' : scope}) # could be based on peer id and not ip but not crucial  
        return str(token)
    
    def authenticate_token(self, token : str, scope : str, ip : str) -> Literal["TOKEN_EXPIRED", "BAD_TOKEN","TOKEN_VALID"]: 
        """authenticate received token 

        Args:
            token (str): _description_

        Returns:
            bool: _description_
        """     
        serializer = Serializer(config.SECRET_KEY)
        
        try: 
            data = serializer.loads(token, max_age=3600)
            if data['ip'] == ip:
                if data['scope'] == scope:
                    return "TOKEN_VALID"
            return "BAD_TOKEN"
        except SignatureExpired:
            return "TOKEN_EXPIRED"
        except BadSignature:
            return "BAD_TOKEN"
    
    def create_user(self, username : str, password : str, scope : str) -> None:
        """creates a new admin user and sets its username and password

        Args:
            username (str): the username of the admin
            password (str): the password of the user 
            scope (str): the scope of the newly created user 
        """
        authentication_hash_query = {'hashed_password' : hash_password(password), 'username' : username, 'scope' : scope}
        self.authentication_table.insert_one(authentication_hash_query)

def hash_password(password : str) -> str: #TODO: use pwd_context
    """ takes in a password and returns the hashed password 

    Args:
        password (str): a password of any type

    Returns:
        str: the hashed password 
    """
    payload = {'password' : password} 
    hash = jwt.encode(payload, config.SECRET_KEY, algorithm='HS256')
    return hash 

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)
    return encoded_jwt



if __name__=='__main__':
    pass
    
