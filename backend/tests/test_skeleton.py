from sqlalchemy import text, inspect

def test_health_and_tables(client, db):
    assert client.get('/health').json() == {'data': {'status': 'ok'}}
    assert db.execute(text('PRAGMA foreign_keys')).scalar() == 1
    assert {'users','employees','departments','positions','skills','employee_skills','sessions','attendance_records'} <= set(inspect(db.bind).get_table_names())

def test_placeholder_rejected(monkeypatch):
    import pytest
    from app.core.config import secret_key
    monkeypatch.setenv('JWT_SECRET_KEY', 'REPLACE_WITH_RANDOM_SECRET')
    monkeypatch.setenv('APP_SECRET_KEY', 'REPLACE_WITH_RANDOM_SECRET')
    with pytest.raises(RuntimeError):
        secret_key()
