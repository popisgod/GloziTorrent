import json 
import torrent_utils

def setup():
    '''
    
    '''
    PEER_UUID = torrent_utils.generate_random_hash()
    PEER_INFO = {'UUID' : PEER_UUID}
    
    with open('settings.json','w') as f:
        data = json.dumps(PEER_INFO)
        f.write(data)

if __name__=='__main__':
    setup()