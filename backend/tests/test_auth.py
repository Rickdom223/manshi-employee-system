from datetime import datetime, timedelta, timezone
import secrets
import jwt
import pytest
from app.models import User
from app.core.security import password_hash, limiter
from app.core.config import secret_key

@pytest.fixture
def admin(db):
    user = User(username='test_admin', password_hash=password_hash.hash('Test-only-password!'))
    db.add(user)
    db.commit()
    limiter.entries.clear()
    return user

@pytest.fixture
def auth(client, admin):
    result = client.post('/api/auth/login', json={'username': 'test_admin', 'password': 'Test-only-password!'})
    return {'X-CSRF-Token':result.json()['data']['csrf_token']}

def test_login_and_me(client, auth):
    response = client.get('/api/auth/me', headers=auth)
    assert response.status_code == 200
    assert response.json()['data']['role']=='ADMIN'
    assert 'password_hash' not in response.json()['data']

def test_bad_password_disabled_and_missing(client, admin, db):
    assert client.post('/api/auth/login', json={'username': admin.username, 'password': 'wrong'}).status_code == 401
    admin.is_active = False
    db.commit()
    assert client.post('/api/auth/login', json={'username': admin.username, 'password': 'Test-only-password!'}).status_code == 401
    assert client.get('/api/auth/me').status_code == 401

@pytest.mark.parametrize('kind', ['expired', 'tampered', 'noexp', 'disabled'])
def test_invalid_tokens(client, admin, db, kind):
    payload = {'sub': str(admin.id), 'exp': datetime.now(timezone.utc) + timedelta(minutes=-1 if kind == 'expired' else 5)}
    if kind == 'noexp':
        payload.pop('exp')
    if kind == 'disabled':
        admin.is_active = False
        db.commit()
    token = jwt.encode(payload, secrets.token_urlsafe(48) if kind == 'tampered' else secret_key(), algorithm='HS256')
    assert client.get('/api/auth/me', headers={'Authorization': 'Bearer ' + token}).status_code == 401

def test_login_rate_limit(client, admin):
    for _ in range(10):
        assert client.post('/api/auth/login', json={'username': 'nobody', 'password': 'wrong'}).status_code == 401
    assert client.post('/api/auth/login', json={'username': 'nobody', 'password': 'wrong'}).status_code == 429
