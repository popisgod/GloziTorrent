from fastapi.testclient import TestClient
from fastapi import status
from trackerAPI import main as app 
from typing import List
from trackerAPI_dependencies.tracker_dao import Peer
import jwt 
from jwt.exceptions import InvalidSignatureError, ExpiredSignatureError
import json, base64

client = TestClient(app())
 
def test_read_root():
    response = client.get('/api')
    assert response.status_code == 200
    assert response.json() == {'tracker_id': 'placeholder'}

def test_announce():
    for i in range(2): 
        peer = Peer(**{"peer_id": f"peer123{str(i)}",
                    "ip": "127.0.0.1", 
                    "port": 8040, 
                    "downloaded" : "0", 
                    "uploaded" : "502", 
                    "left" : "2100", 
                    "event" : "started"})
        info_hash = "hash121"
        
        
        data = {"info_hash": info_hash ,**peer.dict()}
        response  = client.get("/api/announce/", params=data)
    
        assert response.status_code == 20  

    
def test_announce_all():
    # Test case for announce all 
    response  = client.get("api/scrape/")
    
    assert response.status_code == 200
    assert response.json()[0]['info_hash'] == 'hash121' 
    
def test_admin_login():
    credentials = {'username' : 'popisgod12', 
                   'password' : '123346', 
                   'scope' : ['admin'],
                   'grand_type' : 'password'} 
    response = client.post("api/login", data=credentials,
                           headers={"content-type": "application/x-www-form-urlencoded"})



    assert response.status_code == 200
    token = response.json()
    
    # Extracting the payload from the JWT token
    payload = token['access_token'].split('.')[1]

    # Decoding the payload
    decoded_payload = base64.urlsafe_b64decode(payload + '===').decode('utf-8')

    # Parsing the decoded payload as JSON
    payload_data = json.loads(decoded_payload)

    # Extracting the expiry date from the payload
    expiry_date = payload_data['exp']

    #client.headers['Authorization'] = f"{token['token_type']} {token['access_token']}"
    response = client.get('api/admin/')
    
    assert response.status_code == 200
    assert response.json() ==  {'html' : 'admin_page'}


def test_get_all_users(): 
    response = client.get('api/admin/users/')
    
    assert response.status_code == 200
    print(response.json())
    
def test_announce_bad_json_payload():
    # Test case with missing required fields in the JSON payload
    data = { "peer_id": "peer123", "ip": "127.0.0.1", "port": 8080}
    response = client.get("api/announce/", params=data)
    response.json()
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    

def test_read_item_bad_token():
    # Test case for an invalid X-Token header
    response = client.get("api/items/foo", headers={"X-Token": "hailhydra"})
    assert response.status_code == status.HTTP_404_NOT_FOUND

test_admin_login()