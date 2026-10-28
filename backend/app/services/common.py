from sqlalchemy import inspect
from app.core.errors import fail

def get(db, model, id):
    obj = db.get(model, id)
    if obj is None:
        fail(404, 'NOT_FOUND', '记录不存在')
    return obj

def serialize(obj):
    return {c.key: getattr(obj, c.key) for c in inspect(obj).mapper.column_attrs}

def apply(obj, body):
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
