from __future__ import annotations
import datetime
import logging
import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError
from typing import List, Dict, Any, Literal, Annotated, Union, Iterable, Optional
from pydantic import BaseModel
from fastapi import Depends
from pymongo import MongoClient
from passlib.context import CryptContext
if __name__ == '__main__':
    import config
else:
    from . import config

 
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AdminUser(BaseModel):
    ip : str
    username : str


class ActiveUser(BaseModel):
    ip : str
    update : datetime.datetime 
    
class Auth(BaseModel):
    user : AdminUser | None
    message : Literal["TOKEN_VALID","TOKEN_EXPIRED","BAD_TOKEN"]
    scopes : List[str] | None


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
    def __init__(self, dbconnection : MongoClient) -> None:
        """_summary_

        Args:
            dbconnection (MongoClient): _description_
            password (str): _description_
        """
        self.mongo_client = dbconnection
        self.database = self.mongo_client['tracker']
        self.tracker_files_table =  self.database['tracker_files']
        self.authentication_table = self.database['authentication']
        self.refresh_tokens = {}
        self.active_users : Dict[str, ActiveUser] = {}
        
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
        active_uesr = ActiveUser(ip=peer.ip,update=datetime.datetime.now())
        self.active_users[peer.peer_id] = active_uesr
            
        
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
        
    def get_all_active_users(self) -> Dict[str, ActiveUser]:
        return self.active_users
    
    def get_all_tracker_files(self) -> List[TrackerFile]:
        """returns all of the tracker files

        Returns:
            List[TrackerFile]: a list of all of the tracker files stored on the database 
        """
        result: List[Dict[str, Any]] = list(self.tracker_files_table.find())
        logging.info(result)
        return [TrackerFile.from_dict(tracker_file) for tracker_file in result]
    
    def get_tracker_files(self, numwant : int) -> List[TrackerFile]:
        """returns a requested number of the tracker files

        Returns:
            List[TrackerFile]: a list of all of the tracker files stored on the database 
        """
        result: List[Dict[str, Any]] = list(self.tracker_files_table.find(limit=numwant))
        logging.info(result)
        return [TrackerFile.from_dict(tracker_file) for tracker_file in result]    
    
    
    
    def login(self, username : str, password : str, ip : str) -> Dict[str, Any] | None:
        """checks if the username and password are valid and generates a temporary token

        Args:
            password (str): admin password
            username (str): admin username 

        Returns:
            Dict[str, str] | None: an authentication token 
        """
        
        authenticate_hash_query = {'username' : username}
        result = self.authentication_table.find_one(authenticate_hash_query)

        if result: 
            if verify_password(password ,result['hashed_password']):
                data = {'ip' : ip, 'aud' : ['refresh',], 'username' : username}
                refresh_token = self.generate_token(data, result['scopes'], config.REFRESH_TOKEN_EXPIRE_SECONDS)
                self.refresh_tokens[ip] = refresh_token
                
                data = {'ip' : ip, 'aud' : ['access',], 'username' : username}
                access_token = self.generate_token(data ,result['scopes'], config.ACCESS_TOKEN_EXPIRE_SECONDS)
                
                
                return {"access_token": access_token,
                        "refresh_token" : refresh_token,
                        "token_type": "Bearer",
                        "scopes" : result['scopes']}
        return None
        
    def generate_token(self, data : dict[str,str], scopes : List[str], expiration : int = config.ACCESS_TOKEN_EXPIRE_SECONDS) -> str: 
        """ generates an authentication token for the specified scope with a time limit 

        Args:
            scope (str): _description_
            time_limit (int): time limit of the token in seconds 
            ip (str): ip of the user will be used as salt 
        Returns:
            str: _description_
        """
        payload : Dict[str, Any] = {
            **data,
            'scopes' : scopes,
            'exp' : datetime.datetime.now()
                       + datetime.timedelta(seconds=expiration)

        }
        token = jwt.encode(payload=payload, 
                           key=config.SECRET_KEY, 
                           algorithm="HS256")
        return token
    
    def authenticate_token(self, token : str, ip : str, aud : str | Iterable[str] = "access") -> Auth: 
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
                              algorithms=["HS256"],
                              audience=aud)

            if data['ip'] == ip:
                return Auth(message="TOKEN_VALID",user=AdminUser(ip=data['ip'], username=data['username']),scopes=data['scopes'])
            return Auth(message="BAD_TOKEN",user=None,scopes=None)
        except ExpiredSignatureError:
            return Auth(message="TOKEN_EXPIRED",user=None,scopes=None)
        except jwt.InvalidAudienceError:
            return Auth(message="BAD_TOKEN",user=None,scopes=None)
        except InvalidTokenError:
            return Auth(message="BAD_TOKEN",user=None,scopes=None)
    
    def create_user(self, username : str, password : str, scopes : List[str]) -> None:
        """creates a new admin user and sets its username and password

        Args:
            username (str): the username of the admin
            password (str): the password of the user 
            scope (List[str]): the scopes of the newly created user 
        """
        authentication_hash_query = {'hashed_password' : hash_password(password), 
                                     'username' : username,
                                     'scopes' : scopes}
        self.authentication_table.insert_one(authentication_hash_query)
        logging.info(f'created a new user: {username}')

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
    
