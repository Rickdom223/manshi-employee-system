from sqlalchemy import select,func
from app.scripts.init_data import initialize
from app.models import User,Department,Employee,LoginSession
from app.core.security import password_hash
from test_auth import admin,auth
from test_employees import dictionaries,payload,employee

def test_AUTH_01_02_04_initialize(client,db):
    initialize(db);initialize(db)
    assert db.scalar(select(func.count(User.id)))==1
    assert db.scalar(select(func.count(Department.id)))==4
    assert db.scalar(select(func.count(Employee.id)))==0
    response=client.post('/api/auth/login',json={'username':'ljm','password':'Ljm123'})
    assert response.status_code==200
    assert 'HttpOnly' in response.headers['set-cookie'] and 'SameSite=lax' in response.headers['set-cookie']
    assert client.get('/api/auth/me').json()['data']['username']=='ljm'
    assert db.scalar(select(LoginSession)).token_hash!=client.cookies.get('manshi_session')

def test_AUTH_05_06_07_password_logout_csrf(client,auth,db):
    assert client.post('/api/departments',json={'name':'无CSRF'}).status_code==403
    assert client.post('/api/departments',headers=auth|{'Origin':'https://untrusted.invalid'},json={'name':'非法来源'}).status_code==403
    assert client.put('/api/auth/password',headers=auth,json={'old_password':'Test-only-password!','new_password':'New12345','confirm_password':'New12345'}).status_code==200
    user=db.scalar(select(User));hashed=user.password_hash
    initialize(db)
    assert user.password_hash==hashed
    old_cookie=client.cookies.get('manshi_session')
    assert client.post('/api/auth/logout',headers=auth).status_code==200
    client.cookies.set('manshi_session',old_cookie)
    assert client.get('/api/auth/me').status_code==401
    client.cookies.clear()
    assert client.post('/api/auth/login',json={'username':'test_admin','password':'Test-only-password!'}).status_code==401
    assert client.post('/api/auth/login',json={'username':'test_admin','password':'New12345'}).status_code==200
    from datetime import datetime,timedelta,timezone
    session=db.scalar(select(LoginSession).order_by(LoginSession.id.desc()))
    session.expires_at=datetime.now(timezone.utc)-timedelta(seconds=1);db.commit()
    assert client.get('/api/auth/me').status_code==401
    assert client.post('/api/register',json={}).status_code==404
    assert client.post('/api/auth/register',json={}).status_code==404

def test_ATT_01_02_DEP_01(client,auth,employee):
    data={'employee_id':employee['id'],'attendance_date':'2026-10-27','status':'normal','clock_in':'09:00:00','clock_out':'18:00:00'}
    assert client.post('/api/attendance',headers=auth,json=data).status_code==201
    assert client.post('/api/attendance',headers=auth,json=data).status_code==409
    assert client.post('/api/attendance',headers=auth,json=data|{'attendance_date':'2026-10-28','clock_out':'08:00:00'}).status_code==422
    summary=client.get('/api/attendance/monthly?month=2026-10',headers=auth).json()['data'][0]
    assert summary['normal']==1 and summary['absent']==0
    for day,status in [(28,'late'),(29,'early_leave'),(30,'absent'),(31,'leave')]:
        assert client.post('/api/attendance',headers=auth,json=data|{'attendance_date':f'2026-10-{day}','status':status}).status_code==201
    summary=client.get('/api/attendance/monthly?month=2026-10',headers=auth).json()['data'][0]
    assert all(summary[status]==1 for status in ['normal','late','early_leave','absent','leave'])
    assert client.delete(f"/api/departments/{employee['department_id']}",headers=auth).status_code==409
    assert client.delete(f"/api/positions/{employee['position_id']}",headers=auth).status_code==409
