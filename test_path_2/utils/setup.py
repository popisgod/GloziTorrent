import json 
import utils.torrent_utils as torrent_utils
import sqlite3
import os 

def setup_peer():
    '''
    
    '''
    PEER_UUID = torrent_utils.generate_random_hash()
    PEER_INFO = {'UUID' : PEER_UUID}
    
    if os.path.exists('settings.json'):
        return 

    else: 
        with open('settings.json','w') as f:
            data = json.dumps(PEER_INFO)
            f.write(data)

def setup_server():
    '''
    create the sql server 
    '''
    with open('torrent.db','w') as _:
        pass
    with sqlite3.connect('torrent.db') as conn:
        c = conn.cursor()

        c.execute(
            '''
            CREATE TABLE IF NOT EXISTS torrent
            ([file_id] INTEGER PRIMARY KEY, 
            [file_name] TEXT,
            [file_extension] TEXT,
            [file_size] INTEGER,
            [parts] TEXT)
            ''')
        conn.commit()

if __name__=='__main__': 
    pass
