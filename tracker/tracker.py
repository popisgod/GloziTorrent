from fastapi import FastAPI, status
from classy_fastapi import Routable, get, post
import uvicorn
from tracker_dao import Dao, TrackerRequest, TrackerFile
from fastapi.testclient import TestClient
from typing import List, Union
from pydantic import BaseModel


class TrackerResponse(BaseModel):
    TrackerFiles : List[TrackerFile]



class Tracker(Routable):
    def __init__(self, dao : Dao) -> None:
        super().__init__()
        self.__dao = dao
        self.tracker_id = 'placeholder'
    
    @get('/')
    async def root(self) -> str:
        return {'tracker_id' : self.tracker_id}
    
    @get('/annouce')
    async def annouce(self, tracker_request : TrackerRequest) -> TrackerResponse:
        return self.__dao.update_tracker_file(tracker_request.info_hash, tracker_request.peer)

    @post('/register',status_code=status.HTTP_201_CREATED)
    async def register(self, tracker_request : TrackerRequest) -> TrackerResponse:
        return self.__dao.add_tracker_file(tracker_request.info_hash, tracker_request.peer)

def main():
    # Configure the DAO 
    dao = Dao()

    # create the tracker server 
    tracker = Tracker(dao)
    
    app = FastAPI()
    # router memeber inherited from cr.Routable and configured per the annotations.
    app.include_router(tracker.router)
    
    return app 

if __name__=='__main__':
    main()