"""Idempotent, clean V3 installation without fabricated employee data."""
from sqlalchemy import select
from app.core.database import SessionLocal
from app.core.security import password_hash
from app.models import User, Department

DEPARTMENTS = [('PRODUCTION','制琴生产部'),('QUALITY','质量检验部'),('SALES','销售部'),('WAREHOUSE_PURCHASE','仓储采购部')]

def initialize(db):
    for code,name in DEPARTMENTS:
        row=db.scalar(select(Department).where(Department.name==name))
        if row:
            row.code=code; row.is_active=True
        else:
            db.add(Department(code=code,name=name))
    if not db.scalar(select(User.id).where(User.username=='admin')):
        db.add(User(username='admin',password_hash=password_hash.hash('Admin123'),role='SYS_ADMIN'))
    db.commit()

def main():
    import os,json
    mode=os.getenv('INITIAL_DATA_MODE','roster')
    if mode not in {'roster','empty'}:raise RuntimeError('INITIAL_DATA_MODE 只能为 roster 或 empty')
    with SessionLocal() as db:
        initialize(db)
        if mode=='roster':
            from app.services.initial_roster import install_roster
            print(json.dumps(install_roster(db),ensure_ascii=False))
        else:print('空白初始模式：仅四部门和admin，不覆盖已有数据。')

if __name__=='__main__': main()
