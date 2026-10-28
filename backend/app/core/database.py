from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import database_path

class Base(DeclarativeBase):
    pass

def make_engine(path):
    engine = create_engine(f'sqlite:///{path}', connect_args={'check_same_thread': False})
    @event.listens_for(engine, 'connect')
    def foreign_keys(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
    return engine

engine = make_engine(database_path())
SessionLocal = sessionmaker(bind=engine)

def get_db():
    with SessionLocal() as session:
        yield session
