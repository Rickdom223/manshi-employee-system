from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select,func
from sqlalchemy.orm import sessionmaker
from app.models import User,Employee,LeaveRequest
from app.main import app
from app.core.database import get_db
from test_v3_stage1 import setup_hr,employee_body,login

def test_concurrent_approval_only_one_wins(client,db):
    ds,hr=setup_hr(client,db)
    e=client.post('/api/employees',json=employee_body(hr)).json()['data']
    boss=client.post('/api/employees',json=employee_body(hr,'MS003','王主管')).json()['data']
    login(client,'张三')
    lid=client.post('/api/me/leaves',json={'leave_type':'事假','start_date':'2026-11-02','end_date':'2026-11-02','reason':'并发审批验证'}).json()['data']['id']
    login(client,'admin','Admin123');uid=db.scalar(select(User.id).where(User.employee_id==boss['id']))
    client.put(f"/api/admin/departments/{ds[0]['id']}/supervisor",json={'user_id':uid});login(client,'王主管')
    factory=sessionmaker(bind=db.get_bind())
    previous=app.dependency_overrides[get_db]
    def independent_session():
        with factory() as session:yield session
    app.dependency_overrides[get_db]=independent_session
    try:
        def request(decision):return client.post(f'/api/supervisor/leaves/{lid}/review',json={'decision':decision}).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(request,['approve','reject']))
        assert sorted(results)==[200,409]
    finally:app.dependency_overrides[get_db]=previous

def test_account_creation_failure_rolls_back_employee(client,db,monkeypatch):
    ds,hr=setup_hr(client,db)
    import app.services.v3 as service
    def unavailable_hash(_):raise RuntimeError('simulated password hashing failure')
    monkeypatch.setattr(service.password_hash,'hash',unavailable_hash)
    import pytest
    with pytest.raises(RuntimeError):client.post('/api/employees',json=employee_body(hr))
    assert db.scalar(select(func.count(Employee.id)))==1
    assert db.scalar(select(func.count(User.id)))==2
