from fastapi import FastAPI, Depends
from classy_fastapi import Routable, get
from tracker_dao import Dao, Peer, MongoClient
from typing import Annotated, List, AnyStr


class TrackerRequestAnnounce:
    def __init__(self, info_hash : str, peer_id : str, ip : str, port : int
                 , uploaded : str, downloaded : str, left : str, event : str ) -> None:
        self.info_hash = info_hash
        self.peer = Peer(peer_id=peer_id,
                         ip=ip,
                         port=port,
                         downloaded=downloaded,
                         uploaded=uploaded,
                         left=left,
                         event=event)

class Tracker(Routable):
    def __init__(self, dao : Dao) -> None:
        super().__init__()
        self.__dao = dao
        self.tracker_id = 'placeholder'
    
    @get('/')
    async def root(self) -> str:
        return {'tracker_id' : self.tracker_id} # type: ignore
    
    @get('/announce/')
    async def announce(self, tracker_request_announce :  Annotated[TrackerRequestAnnounce, Depends(TrackerRequestAnnounce)]) -> List[Peer]:
        return self.__dao.update_tracker_files(tracker_request_announce.info_hash, tracker_request_announce.peer)

def main():
    # Configure the DAO and database
    client = MongoClient("localhost", 27017)  
    dao = Dao(dbconnection=client)

    # create the tracker server 
    tracker = Tracker(dao)
    
    app = FastAPI()
    # router memeber inherited from cr.Routable and configured per the annotations.
    app.include_router(tracker.router)
    
    return app 

if __name__=='__main__':
    main()