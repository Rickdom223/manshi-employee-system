"""Compatibility entry point: run migrations and the SPEC's non-destructive initializer."""
from app.scripts.init_data import initialize

def main():
    from alembic.config import Config
    from alembic import command
    from app.core.config import BACKEND
    from app.scripts.init_data import main as seed
    command.upgrade(Config(str(BACKEND/'alembic.ini')),'head')
    seed()

if __name__=='__main__':main()
