from datetime import datetime,timezone,date
from io import BytesIO
import pytest
from openpyxl import Workbook
from sqlalchemy import select,func
from app.models import User,Employee,Position,LoginSession,DepartmentSupervisor,PunchRecord,Salary,EmploymentEvent
from app.core.security import password_hash,limiter
from test_v3_stage1 import setup_hr,employee_body,login

@pytest.mark.parametrize('role',['EMPLOYEE','SUPERVISOR','HR','SYS_ADMIN'])
def test_role_permission_matrix(client,db,role):
    ds,hr=setup_hr(client,db)
    e=client.post('/api/employees',json=employee_body(hr)).json()['data']
    if role=='SYS_ADMIN':login(client,'admin','Admin123')
    elif role=='HR':login(client,'李人事')
    else:
        login(client,'admin','Admin123');uid=db.scalar(select(User.id).where(User.employee_id==e['id']))
        client.patch(f'/api/admin/users/{uid}/role',json={'role':role});login(client,'张三')
    for path,owner in [('/api/employees','HR'),('/api/attendance/monthly?month=2026-10','HR'),('/api/attendance/rules','HR'),('/api/hr/leaves','HR'),('/api/salaries','HR'),('/api/dashboard/hr','HR'),('/api/admin/users','SYS_ADMIN'),('/api/admin/departed-users','SYS_ADMIN'),('/api/admin/audit-logs','SYS_ADMIN'),('/api/supervisor/leaves','SUPERVISOR')]:
        assert client.get(path).status_code==(200 if role==owner else 403),(role,path)
    for path in ['/api/me/employee','/api/me/salaries','/api/me/leaves','/api/me/attendance?month=2026-10']:
        assert client.get(path).status_code==(403 if role=='SYS_ADMIN' else 200)

def test_csrf_origin_session_hash_and_no_credentials_disclosure(client,db):
    ds,hr=setup_hr(client,db)
    r=client.get('/api/auth/me');assert 'password' not in r.text and 'hash' not in r.text
    assert r.json()['data']['employee']['id']==hr['id']
    assert 'SALARY_MANAGE' in r.json()['data']['permissions']
    cookie=client.cookies.get('manshi_session')
    session=db.scalar(select(LoginSession).where(LoginSession.revoked_at==None).order_by(LoginSession.id.desc()))
    assert session.token_hash!=cookie and len(session.token_hash)==64
    assert session.csrf_token_hash!=client.headers['X-CSRF-Token']
    headers=dict(client.headers);client.headers.pop('X-CSRF-Token')
    assert client.post('/api/employees',json=employee_body(hr)).status_code==403
    client.headers.update(headers);client.headers['Origin']='https://attacker.invalid'
    assert client.post('/api/employees',json=employee_body(hr)).status_code==403
    client.headers['Origin']='http://testserver'
    login(client,'admin','Admin123');r=client.get('/api/admin/users')
    assert 'password' not in r.text and 'hash' not in r.text
    assert client.get('/api/register').status_code==404 and client.post('/api/auth/register',json={}).status_code==404

def test_login_rate_limit_only_failures_and_logout_revocation(client,db):
    ds,hr=setup_hr(client,db)
    for i in range(12):login(client,'李人事')
    assert client.post('/api/auth/logout').status_code==200
    assert client.get('/api/auth/me').status_code==401
    for i in range(10):assert client.post('/api/auth/login',json={'username':'unknown','password':'wrong'}).status_code==401
    assert client.post('/api/auth/login',json={'username':'unknown','password':'wrong'}).status_code==429

def test_atomic_bootstrap_failure_and_employee_position_rules(client,db):
    from app.scripts.initialize_v3 import initialize
    initialize(db);login(client,'admin','Admin123')
    department=client.get('/api/departments').json()['data'][0]
    # Wrong department fails without leaving a partial position or employee.
    body=dict(employee_no='MS001',name='测试HR',department_id=999,position_name='人事负责人',hire_date='2026-01-01')
    assert client.post('/api/admin/bootstrap-first-hr',json=body).status_code==422
    assert db.scalar(select(func.count(Position.id)))==0
    body['department_id']=department['id'];assert client.post('/api/admin/bootstrap-first-hr',json=body).status_code==200
    login(client,'测试HR');hr=client.get('/api/me/employee').json()['data']
    assert client.patch(f"/api/positions/{hr['position_id']}",json={'is_active':False}).status_code==200
    assert client.post('/api/employees',json=employee_body(hr)).status_code==422
    assert db.scalar(select(func.count(Employee.id)))==1 and db.scalar(select(func.count(User.id)))==2
    assert client.patch(f"/api/positions/{hr['position_id']}",json={'is_active':None}).status_code==422
    assert client.patch(f"/api/employees/{hr['id']}",json={'name':'更名HR'}).status_code==200
    assert client.get('/api/me/employee').json()['data']['account_username']=='测试HR'

def test_excel_invalid_file_duplicate_rows_dates_and_template(client,db):
    ds,hr=setup_hr(client,db)
    for name,data in [('x.xls',b'bad'),('x.xlsx',b'bad'),('x.xlsx',b'')]:
        assert client.post('/api/employees/import',files={'file':(name,data)}).status_code==422
    assert client.get('/api/employees/import-template').headers['content-type'].startswith('application/vnd.openxmlformats')
    wb=Workbook();ws=wb.active;ws.append(['工号','姓名','部门','职位','入职日期']);ws.append(['MS002','日期错误',ds[0]['name'],'人事负责人','not-date']);ws.append(['MS003','正确员工',ds[0]['name'],'人事负责人','2026-01-01'])
    output=BytesIO();wb.save(output)
    result=client.post('/api/employees/import',files={'file':('员工.xlsx',output.getvalue())}).json()
    assert result['success_count']==1 and not result['data'][0]['success']
    assert db.scalar(select(func.count(Employee.id)))==2

def test_transfer_removes_supervisor_and_retains_leave_snapshot(client,db):
    ds,hr=setup_hr(client,db)
    boss=client.post('/api/employees',json=employee_body(hr)).json()['data']
    other=client.post('/api/positions',json={'code':'SALES01','name':'销售专员','department_id':ds[2]['id'],'grade':'L1'}).json()['data']
    login(client,'admin','Admin123');uid=db.scalar(select(User.id).where(User.employee_id==boss['id']))
    assert client.put(f"/api/admin/departments/{ds[0]['id']}/supervisor",json={'user_id':uid}).status_code==200
    login(client,'张三');leave=client.post('/api/me/leaves',json={'leave_type':'事假','start_date':'2026-11-02','end_date':'2026-11-02','reason':'私事'}).json()['data']
    login(client,'李人事');assert client.patch(f"/api/employees/{boss['id']}",json={'department_id':ds[2]['id'],'position_id':other['id']}).status_code==200
    assert not db.get(DepartmentSupervisor,ds[0]['id'])
    login(client,'张三');assert client.get('/api/me/leaves').json()['data'][0]['department_id']==ds[0]['id']
