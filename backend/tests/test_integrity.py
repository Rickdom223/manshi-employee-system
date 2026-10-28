import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text, select
from app.models import Position, EmployeeSkill
from test_auth import admin, auth

def test_foreign_keys_enforced(db):
    db.add(Position(code='BAD', name='无效外键', department_id=999))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    assert not db.scalar(select(Position))

def test_validation_envelope_and_missing(client, auth):
    response = client.get('/api/employees', headers=auth, params={'page': 0})
    assert response.status_code == 422
    assert 'error' in response.json() and 'detail' not in response.json()
    assert client.get('/api/employees/999', headers=auth).status_code == 404
    assert client.delete('/api/employees/999/skills/1', headers=auth).status_code == 404

def test_security_config(monkeypatch):
    from app.core.config import token_minutes, database_path
    monkeypatch.setenv('ACCESS_TOKEN_EXPIRE_MINUTES', '0')
    with pytest.raises(RuntimeError):
        token_minutes()
    monkeypatch.setenv('DATABASE_PATH', 'relative.sqlite3')
    with pytest.raises(RuntimeError):
        database_path()
