import re
import logging
import uvicorn
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Annotated, List, Dict, Callable
from classy_fastapi import Routable, get, post
from trackerAPI_dependencies.tracker_dao import TrackerDao, Peer, TrackerFile, ActiveUser, AdminUser
from pymongo import MongoClient
from starlette.authentication import requires
from starlette.authentication import AuthCredentials, AuthenticationError
from starlette.requests import HTTPConnection
from starlette.middleware.authentication import AuthenticationMiddleware


# logging configuration 
logging.basicConfig(filename='tracker.log', 
                    level=logging.INFO, 
                    filemode='w', 
                    format='%(asctime)s - %(message)s',
                    datefmt='%d-%b-%y %H:%M:%S')

# authentication scheme 
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", 
                                     scopes={"admin" : "administrative rights",
                                            "user" : "basic rights"})


class ExtraAnnounceOptions(BaseModel): 
    """_summary_

    Args:
        BaseModel (_type_): _description_

    Returns:
        _type_: _description_
    """
    compact_mode : bool = False
    no_peer_id : bool = False
    numwant : int | None = None


class TrackerRequestAnnounce(BaseModel):
    """_summary_

    Args:
        BaseModel (_type_): _description_
    """
    info_hash : str
    peer : Annotated[Peer, Depends()]
    options : Annotated[ExtraAnnounceOptions, Depends()]

class TrackerAPI(Routable):
    """_summary_

    Args:
        Routable (_type_): _description_
    """
    def __init__(self, dao : TrackerDao) -> None:
        super().__init__()
        self._dao : TrackerDao = dao
        self.tracker_id = 'placeholder'
        self.blacklisted : List[str] = []

    
    async def authenticate(self, conn : HTTPConnection) -> tuple[AuthCredentials, AdminUser] | None:
        auth_token = conn.headers.get("Authorization", None)
        if auth_token is None:
            return 
        
        if conn.client is not None:
            if conn.client.host in self.blacklisted:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='client is banned')
            
            scheme, auth_token  = auth_token.split()
            auth = self._dao.authenticate_token(auth_token, 
                                                       conn.client.host, 
                                                       "access")
            
            
            if auth.message == 'TOKEN_VALID':
                if auth.scopes is not None and auth.user is not None: 
                    return AuthCredentials(auth.scopes), auth.user
            elif auth.message == 'TOKEN_EXPIRED':
                        raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
                        )
            elif auth.message == 'BAD_TOKEN':
                        raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='authentication process failed')
        else: 
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Client information is missing')

    @get('/')
    async def root(self) -> Dict[str, str]:
        return {'tracker_id' : self.tracker_id} 
    
    @get('/announce/')
    async def announce(self, tracker_request_announce :  Annotated[TrackerRequestAnnounce, Depends(TrackerRequestAnnounce)]) -> List[Peer]:
        return self._dao.update_tracker_files(info_hash=tracker_request_announce.info_hash, 
                                               peer=tracker_request_announce.peer, 
                                               **tracker_request_announce.options.dict())

    @get('/scrape/')
    async def scrape(self) -> List[TrackerFile]:
        return self._dao.get_all_tracker_files()
    
    @post('/token')
    async def token(self, form_data : Annotated[OAuth2PasswordRequestForm, Depends()], request : Request) -> Dict[str, str]:
        # authenticate the password and get the 
        if request.client:
            auth = self._dao.login(form_data.username, form_data.password, form_data.scopes, request.client.host)
            if auth:
                return auth

            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Incorrect username or password')
        
        else: 
           raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Client information is missing')       
    
    @get('/admin/')
    @requires(scopes=['admin'])
    async def get_admin_page(self, request : Request) -> Dict[str,str] | None:
        return {'html' : 'admin_page'}

    @get('/admin/users/')
    @requires(scopes=['admin'])
    async def get_users(self, request : Request) -> Dict[str,ActiveUser] | None:
        return self._dao.get_all_active_users()

    @post('/admin/blacklist')
    @requires(scopes=['admin'])
    async def blacklist(self, ips : list[str]) -> Dict[str,List[str]]:
        ip_pattern = r'^((([01]?[0-9]?[0-9]|2[0-4][0-9]|25[0-5])\.){3})([01]?[0-9]?[0-9]|2[0-4][0-9]|25[0-5])$'
        for ip in ips:
            if re.match(ip_pattern, ip):
                self.blacklisted.append(ip)
        return {'blacklisted' : self.blacklisted}
    
    @get('/admin/blacklist/')
    @requires(scopes=['admin'])
    async def get_blacklist(self) -> Dict[str,List[str]]:
        return {'blacklisted' : self.blacklisted}
    
def main():
    # Configure the DAO and database
    client = MongoClient("localhost", 27017)  
    dao = TrackerDao(dbconnection=client)
    dao.create_user('popisgod12','123346',['admin','user'])
    
            
    # create the tracker server 
    trackerAPI = TrackerAPI(dao)
    
    TrackerAPP = FastAPI()
    # router memeber inherited from cr.Routable and configured per the annotations.
    TrackerAPP.include_router(trackerAPI.router)
    TrackerAPP.add_middleware(AuthenticationMiddleware, backend=trackerAPI)
    
    
    return TrackerAPI 

if __name__=='__main__':
        uvicorn.run("trackerAPI:main", port=5000, log_level="info", factory=True, )
