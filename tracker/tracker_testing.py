from fastapi.testclient import TestClient
from tracker import main as app
from fastapi import status


client = TestClient(app())
 

def test_read_root():
    response = client.get('/')
    assert response.status_code == 200
    assert response.json() == {'tracker_id': 'placeholder'}

def test_register():
    response = client.post("/register", params={"info_hash": "hash123", "peer": {"peer_id": "peer123", "ip": "127.0.0.1", "port": 8080}})
    assert response.status_code == 201
    # Assert the response based on the expected result from `add_tracker_file` in your DAO

def test_announce():
    response = client.get("/announce", params={"info_hash": "hash123", "peer": {"peer_id": "peer123", "ip": "127.0.0.1", "port": 8080}})
    assert response.status_code == 200
    # Assert the response based on the expected result from `update_tracker_file` in your DAO

def test_announce_bad_json_payload():
    # Test case with missing required fields in the JSON payload
    response = client.get("/announce", params={"peer": {"peer_id": "peer123", "ip": "127.0.0.1", "port": 8080}})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

def test_read_item_bad_token():
    # Test case for an invalid X-Token header
    response = client.get("/items/foo", headers={"X-Token": "hailhydra"})
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_read_inexistent_item():
    # Test case for requesting an inexistent item
    response = client.get("/items/baz", headers={"X-Token": "coneofsilence"})
    assert response.status_code == status.HTTP_404_NOT_FOUND
    



