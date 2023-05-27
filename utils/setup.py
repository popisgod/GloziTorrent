import json 
import utils.torrent_utils as torrent_utils

def setup_peer():
    '''
    
    '''
    PEER_UUID = torrent_utils.generate_random_hash()
    PEER_INFO = {'UUID' : PEER_UUID}
    
    with open('settings.json','w') as f:
        data = json.dumps(PEER_INFO)
        f.write(data)

def setup_server():
    '''
    create the sql server 
    '''
    

if __name__=='__main__': 
    pass
