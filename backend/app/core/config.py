import os
from pathlib import Path
from dotenv import load_dotenv

BACKEND = Path(__file__).resolve().parents[2]
load_dotenv(BACKEND / '.env')

def secret_key():
    value = os.getenv('SESSION_SECRET_KEY') or os.getenv('APP_SECRET_KEY') or os.getenv('JWT_SECRET_KEY', '')
    if len(value) < 32 or value.startswith('REPLACE_'):
        raise RuntimeError('请设置至少32字符的随机 APP_SECRET_KEY（兼容旧JWT_SECRET_KEY），不能使用占位值')
    return value

def token_minutes():
    value = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', '30'))
    if not 1 <= value <= 1440:
        raise RuntimeError('ACCESS_TOKEN_EXPIRE_MINUTES 必须为 1–1440')
    return value

def database_path():
    value=os.getenv('DATABASE_PATH')
    if not value and os.getenv('DATABASE_URL'):
        from sqlalchemy.engine import make_url
        url=make_url(os.environ['DATABASE_URL'])
        if url.drivername!='sqlite' or not url.database or url.database==':memory:':
            raise RuntimeError('本版DATABASE_URL仅允许持久化SQLite路径')
        candidate=Path(url.database)
        value=str(candidate if candidate.is_absolute() else (BACKEND/candidate).resolve())
    path = Path(value or str(BACKEND / 'data' / 'manshi.sqlite3'))
    if not path.is_absolute():
        raise RuntimeError('DATABASE_PATH 必须为绝对路径')
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
