from datetime import date,datetime
from sqlalchemy import select,func
from app.models import User,Employee,DepartmentSupervisor,EmploymentEvent,PunchRecord,AttendanceRule,LeaveRequest,Salary
from test_v3_stage1 import setup_hr,employee_body,login

def create(c,hr,no,name):
    r=c.post('/api/employees',json=employee_body(hr,no,name));assert r.status_code==200,r.text
    return r.json()['data']

def test_departure_rehire_sessions_history(client,db):
    ds,hr=setup_hr(client,db);e=create(client,hr,'MS002','张三')
    login(client,'张三');old_cookie=client.cookies.get('manshi_session');uid=client.get('/api/auth/me').json()['data']['id']
    login(client,'admin','Admin123');assert client.patch(f'/api/admin/users/{uid}/role',json={'role':'HR'}).status_code==200
    login(client,'李人事');assert client.post('/api/salaries',json={'employee_id':e['id'],'year':2026,'month':1,'amount':'1234.56'}).status_code==200
    r=client.post(f"/api/employees/{e['id']}/leave",json={'event_date':'2026-02-01'});assert r.status_code==200,r.text
    client.cookies.set('manshi_session',old_cookie)
    assert client.get('/api/auth/me').status_code==401
    client.cookies.clear();login(client,'admin','Admin123')
    assert client.post(f'/api/admin/users/{uid}/enable').status_code==422
    assert client.get('/api/admin/departed-users').json()['data'][0]['disabled_reason']=='EMPLOYEE_LEFT'
    assert client.get('/api/salaries').status_code==403
    login(client,'李人事');r=client.post(f"/api/employees/{e['id']}/rehire",json={'event_date':'2026-03-01'});assert r.status_code==200,r.text
    u=db.get(User,uid);assert u.role=='EMPLOYEE' and not u.is_active
    assert db.scalar(select(func.count(Salary.id)))==1
    assert db.scalar(select(func.count(EmploymentEvent.id)))==2
    login(client,'admin','Admin123');assert client.post(f'/api/admin/users/{uid}/enable').status_code==200
    assert client.post(f'/api/admin/users/{uid}/reset-password',json={'new_password':'abc123'}).status_code==422
    assert client.post(f'/api/admin/users/{uid}/reset-password',json={'new_password':'Bb123'}).status_code==200
    login(client,'张三','Bb123');assert client.get('/api/me/salaries').json()['data'][0]['amount']=='1234.56'

def test_punch_rules_and_salary_isolation(client,db,monkeypatch):
    ds,hr=setup_hr(client,db);e=create(client,hr,'MS002','张三');other=create(client,hr,'MS003','李四')
    import app.routers.v3_business as business
    monkeypatch.setattr(business,'business_now',lambda:datetime(2026,10,26,9,5))
    assert client.post('/api/attendance/rules',json={'effective_date':'2026-01-01','weekdays':[0,1,2,3,4],'start_time':'09:00','end_time':'18:00','late_grace_minutes':3}).status_code==200
    assert client.post('/api/salaries',json={'employee_id':e['id'],'year':2026,'month':10,'amount':'5000.01'}).status_code==200
    assert client.post('/api/salaries',json={'employee_id':e['id'],'year':2026,'month':10,'amount':'1'}).status_code==409
    login(client,'张三')
    assert client.post('/api/me/punch-out').status_code==409
    assert client.post('/api/me/punch-in',json={'employee_id':other['id'],'time':'fake'}).status_code==200
    assert client.post('/api/me/punch-in').status_code==409
    monkeypatch.setattr(business,'business_now',lambda:datetime(2026,10,26,17,0))
    assert client.post('/api/me/punch-out').status_code==200
    assert client.get('/api/me/salaries').json()['data'][0]['amount']=='5000.01'
    assert client.get(f"/api/me/salaries?employee_id={other['id']}").status_code==403
    assert client.get(f"/api/salaries?employee_id={other['id']}").status_code==403
    assert client.get('/api/me/attendance?month=0000-01').status_code==422
    assert client.get('/api/me/attendance?month=2026-13').status_code==422
    summary=client.get('/api/me/attendance?month=2026-10').json()['data']
    assert summary['late_count']==1 and summary['early_count']==1 and summary['actual_days']==1

def test_supervisor_department_self_overlap_and_pending(client,db):
    ds,hr=setup_hr(client,db);e=create(client,hr,'MS002','张三');boss=create(client,hr,'MS003','王主管')
    login(client,'张三');r=client.post('/api/me/leaves',json={'leave_type':'年假','start_date':'2026-10-28','end_date':'2026-10-30','reason':'休假'})
    assert r.status_code==200 and '尚未配置主管' in r.json()['message'];lid=r.json()['data']['id']
    login(client,'李人事');assert client.post(f'/api/supervisor/leaves/{lid}/review',json={'decision':'approve'}).status_code==403
    login(client,'admin','Admin123')
    boss_uid=db.scalar(select(User.id).where(User.employee_id==boss['id']))
    assert client.put(f"/api/admin/departments/{ds[1]['id']}/supervisor",json={'user_id':boss_uid}).status_code==422
    assert client.put(f"/api/admin/departments/{ds[0]['id']}/supervisor",json={'user_id':boss_uid}).status_code==200
    login(client,'王主管');assert client.get('/api/supervisor/leaves').json()['total']==1
    assert client.post(f'/api/supervisor/leaves/{lid}/review',json={'decision':'approve'}).status_code==200
    assert client.post(f'/api/supervisor/leaves/{lid}/review',json={'decision':'reject'}).status_code==409
    own=client.post('/api/me/leaves',json={'leave_type':'病假','start_date':'2026-10-28','end_date':'2026-10-28','reason':'就诊'}).json()['data']['id']
    assert client.post(f'/api/supervisor/leaves/{own}/review',json={'decision':'approve'}).status_code==403
    login(client,'张三');overlap=client.post('/api/me/leaves',json={'leave_type':'事假','start_date':'2026-10-29','end_date':'2026-10-29','reason':'重叠'}).json()['data']['id']
    login(client,'王主管');assert client.post(f'/api/supervisor/leaves/{overlap}/review',json={'decision':'approve'}).status_code==409
    assert db.get(LeaveRequest,overlap).status=='pending'
    # Assignment removal makes the former supervisor unable to approve pending work.
    login(client,'admin','Admin123');client.delete(f"/api/admin/departments/{ds[0]['id']}/supervisor")
    login(client,'王主管');assert client.post(f'/api/supervisor/leaves/{overlap}/review',json={'decision':'reject'}).status_code==403
