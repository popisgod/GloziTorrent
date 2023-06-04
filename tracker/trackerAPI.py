import uvicorn
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, SecurityScopes
from pydantic import BaseModel
from typing import Annotated, List, Dict
from classy_fastapi import Routable, get, post
from .trackerAPI_dependencies import TrackerDao, Peer, TrackerFile
from pymongo import MongoClient


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


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


class Tracker(Routable):
    """_summary_

    Args:
        Routable (_type_): _description_
    """
    
    def __init__(self, dao : TrackerDao) -> None:
        super().__init__()
        self._dao : TrackerDao = dao
        self.tracker_id = 'placeholder'
    
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
    
    @post('/admin/login')
    async def login(self, form_data : Annotated[OAuth2PasswordRequestForm, Depends()], request : Request) -> Dict[str, str]:
        # authenticate the password and get the 
        if request.client:
            auth = self._dao.login_admin(form_data.username, form_data.password, request.client.host)
            if auth:
                return auth
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Incorrect username or password')
        else: 
           raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Client information is missing')       
    
    @get('/admin/')
    async def get_admin_page(self, token : Annotated[str, Depends(oauth2_scheme)], request : Request) -> Dict[str,str]:
        if request.client is not None:
            auth_status = self._dao.authenticate_token(token, 'admin', request.client.host)

            if auth_status == 'TOKEN_VALID':
                return {'token_status' : auth_status}
            elif auth_status == 'TOKEN_EXPIRED':
                        raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
                        )
            elif auth_status == 'BAD_TOKEN':
                        raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='authentication process failed')
        else: 
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Client information is missing')

    @get('/admin/refresh')
    async def refresh_token(self, refresh_token : Annotated[str, Depends(oauth2_scheme)], request : Request) -> Dict[str,str]:
        pass


def main():
    # Configure the DAO and database
    client = MongoClient("localhost", 27017)  
    dao = TrackerDao(dbconnection=client)
    dao.create_user('popisgod1','12346','admin')
    
    # create the tracker server 
    tracker = Tracker(dao)
    
    app = FastAPI()
    # router memeber inherited from cr.Routable and configured per the annotations.
    app.include_router(tracker.router)
    
    return app 

if __name__=='__main__':
        uvicorn.run("tracker:main", port=5000, log_level="info", factory=True, )
