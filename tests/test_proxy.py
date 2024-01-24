from fastapi import FastAPI
from fastapi.testclient import TestClient
from guardette import Guardette
from guardette.proxy import PROXY_HOST_HEADER
from unittest.mock import patch

app = FastAPI()

guardette = Guardette(policy_path="tests/test_policy.yml")
guardette.to_fastapi(app)

client = TestClient(app)

secrets = {
    'CLIENT_SECRET': 'test'
}


async def get_secret(key):
    return secrets.get(key)


@patch('guardette.secrets.ConfigSecretsManager.get', side_effect=get_secret)
def test_yc(mock_get):
    response = client.get('/v0/item/8863.json',
                          headers={
                              PROXY_HOST_HEADER: 'hacker-news.firebaseio.com',
                              'Authorization': secrets['CLIENT_SECRET']
                            })
    assert response.status_code == 200, response.text
    assert response.json()['title'] == guardette.config.redact_token

