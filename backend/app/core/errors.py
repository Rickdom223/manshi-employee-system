from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

def fail(status, code, message):
    raise HTTPException(status, detail={'code': code, 'message': message})

def commit(db, code='UNIQUE_CONFLICT', message='编码、名称或关联已存在'):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        fail(409, code, message)
