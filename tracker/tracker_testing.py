from fastapi.testclient import TestClient
from tracker import main as app
from fastapi import status
import json

client = TestClient(app())
 
 
def test_read_root():
    response = client.get('/')
    assert response.status_code == 200
    assert response.json() == {'tracker_id': 'placeholder'}

# deprecated test 
# def test_register():
#     data = {"info_hash": "hash121", "peer": {"peer_id": "peer123", "ip": "127.0.0.1", "port": 8080}}
#     response = client.post("/register/", json=data)
#     assert response.reason_phrase == 'Created'
#     assert response.status_code == 201
#     assert response.json()['tracker_file']['info_hash'] == 'hash121'
#     # Assert the response based on the expected result from `add_tracker_file` in your DAO


def test_announce():
    data = {"info_hash": "hash121", "peer_id": "peer1233", "ip": "127.0.0.1", "port": 8040, 
            "downloaded" : 0, "uploaded" : "502", "left" : "2100", "event" : "started"}
    
    response = client.get("/announce/", params=data)
    assert response.status_code == 200


def test_announce_bad_json_payload():
    # Test case with missing required fields in the JSON payload
    data = {"peer": {"peer_id": "peer123", "ip": "127.0.0.1", "port": 8080}}
    response = client.post("/announce/", params=json.dumps(data))
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

def test_read_item_bad_token():
    # Test case for an invalid X-Token header
    response = client.get("/items/foo", headers={"X-Token": "hailhydra"})
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_read_inexistent_item():
    # Test case for requesting an inexistent item
    response = client.get("/items/baz", headers={"X-Token": "coneofsilence"})
    assert response.status_code == status.HTTP_404_NOT_FOUND
    
test_announce()

