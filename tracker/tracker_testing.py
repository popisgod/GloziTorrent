from fastapi.testclient import TestClient
from fastapi import status
from .trackerAPI import main as app 
from typing import List
from .trackerAPI_dependencies import Peer


client = TestClient(app())
 
def test_read_root():
    response = client.get('/')
    assert response.status_code == 200
    assert response.json() == {'tracker_id': 'placeholder'}

def test_announce():
    peer = Peer(**{"peer_id": "peer1233",
                "ip": "127.0.0.1", 
                "port": 8040, 
                "downloaded" : "0", 
                "uploaded" : "502", 
                "left" : "2100", 
                "event" : "started"})
    info_hash = "hash121"
    
    
    data = {"info_hash": info_hash ,**peer.dict()}
    response  = client.get("/announce/", params=data)
    
    assert response.status_code == 200
    assert response.json()[0] == peer.dict()
    
    data['peer_id'] = 'hello'
    response = client.get("/announce/", params=data)
    
    assert len(response.json()) == 2
    
def test_announce_all():
    # Test case for announce all 
    response  = client.get("/scrape/")
    
    assert response.status_code == 200
    assert response.json()[0]['info_hash'] == 'hash121' 
    
def test_admin_login():
    credentials = {'username' : 'popisgod1', 'password' : '12346'} 
    response = client.post("/admin/login", data=credentials,
                           headers={"content-type": "application/x-www-form-urlencoded"})

    assert response.status_code == 200
    token = response.json()
    
    client.headers['Authorization'] = f"{token['token_type']} {token['access_token']}"
    response = client.get('/admin/')
    
    assert response.status_code == 200
    assert response.json() ==  {'token_status' : 'TOKEN_VALID'}

    
    
def test_announce_bad_json_payload():
    # Test case with missing required fields in the JSON payload
    data = { "peer_id": "peer123", "ip": "127.0.0.1", "port": 8080}
    response = client.get("/announce/", params=data)
    response.json()
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    

def test_read_item_bad_token():
    # Test case for an invalid X-Token header
    response = client.get("/items/foo", headers={"X-Token": "hailhydra"})
    assert response.status_code == status.HTTP_404_NOT_FOUND

test_announce()