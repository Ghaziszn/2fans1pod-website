import pytest
from app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c

def test_health(client):
    r = client.get('/healthz')
    assert r.status_code == 200
    assert r.get_json().get('ok') is True
