import os
import secrets
import pytest
os.environ['JWT_SECRET_KEY'] = secrets.token_urlsafe(48)
os.environ['APP_SECRET_KEY'] = os.environ['JWT_SECRET_KEY']
os.environ['ALLOWED_ORIGINS']='http://testserver,http://127.0.0.1:3000'
os.environ['INITIAL_DATA_MODE']='empty'
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from app.core.database import Base, get_db, make_engine
from app.main import app
from app import models

@pytest.fixture
def db(tmp_path):
    engine = make_engine(tmp_path / 'isolated.sqlite3')
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        yield session
    engine.dispose()

@pytest.fixture
def client(db):
    def override_db():
        try:yield db
        except Exception:
            db.rollback()
            raise
    app.dependency_overrides[get_db] = override_db
    from app.core.security import limiter
    limiter.entries.clear()
    with TestClient(app,headers={'Origin':'http://testserver'}) as c:
        yield c
    app.dependency_overrides.clear()
