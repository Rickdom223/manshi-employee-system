import pytest
from io import BytesIO
from sqlalchemy import select, func
from openpyxl import Workbook
from app.models import User, Employee, Department, Position, LoginSession
from app.scripts.initialize_v3 import initialize

def login(c,name,password='Aa123'):
    r=c.post('/api/auth/login',json={'username':name,'password':password})
    assert r.status_code==200,r.text
    c.headers['X-CSRF-Token']=r.json()['data']['csrf_token']
    return r.json()['data']

def setup_hr(c,db):
    initialize(db);login(c,'admin','Admin123')
    ds=c.get('/api/departments').json()['data']
    r=c.post('/api/admin/bootstrap-first-hr',json={'employee_no':'MS001','name':'李人事','department_id':ds[0]['id'],'position_name':'人事负责人','grade':'L3','hire_date':'2026-01-01'})
    assert r.status_code==200,r.text
    e=r.json()['data'];login(c,'李人事')
    return ds,e

def employee_body(e,number='MS002',name='张三'):
    return dict(employee_no=number,name=name,department_id=e['department_id'],position_id=e['position_id'],hire_date='2026-01-01')

def test_clean_bootstrap_and_no_department_writes(client,db):
    initialize(db);initialize(db)
    assert db.scalar(select(func.count(Department.id)))==4
    assert [(u.username,u.role,u.employee_id) for u in db.scalars(select(User))]==[('admin','SYS_ADMIN',None)]
    login(client,'admin','Admin123')
    for method,path in [('post','/api/departments'),('patch','/api/departments/1'),('delete','/api/departments/1')]:
        assert getattr(client,method)(path).status_code in (403,404,405)

def test_auto_account_collision_promotion_and_rename(client,db):
    ds,hr=setup_hr(client,db)
    first=client.post('/api/employees',json=employee_body(hr)).json()['data']
    second=client.post('/api/employees',json=employee_body(hr,'MS003')).json()['data']
    assert first['account_username']=='张三' and second['account_username']=='张三-MS003'
    assert client.post('/api/employees',json=employee_body(hr)).status_code==409
    assert db.scalar(select(func.count(Employee.id)))==3
    login(client,'张三');uid=client.get('/api/auth/me').json()['data']['id']
    login(client,'admin','Admin123')
    assert client.patch(f'/api/admin/users/{uid}/role',json={'role':'HR'}).status_code==200
    login(client,'张三')
    assert client.get('/api/auth/me').json()['data']['role']=='HR'
    edited=employee_body(hr,name='张三新姓名')
    assert client.patch(f"/api/employees/{first['id']}",json=edited).status_code==200
    assert client.get('/api/me/employee').json()['data']['account_username']=='张三'
    assert client.post('/api/admin/bootstrap-first-hr',json={}).status_code==403

@pytest.mark.parametrize('password',['abcdef','ABC123','abc123','123456','Ａa1'])
def test_password_rejected(client,db,password):
    initialize(db);login(client,'admin','Admin123')
    assert client.post('/api/auth/change-password',json={'old_password':'Admin123','new_password':password,'confirm_password':password}).status_code==422

def test_password_change_revokes_all_and_persists(client,db):
    initialize(db);login(client,'admin','Admin123')
    assert client.post('/api/auth/change-password',json={'old_password':'wrong','new_password':'Ab1','confirm_password':'Ab1'}).status_code==400
    assert client.post('/api/auth/change-password',json={'old_password':'Admin123','new_password':'Ab1','confirm_password':'Ab1'}).status_code==200
    assert client.get('/api/auth/me').status_code==401
    initialize(db);login(client,'admin','Ab1')

def test_excel_partial_success_and_permissions(client,db):
    ds,hr=setup_hr(client,db)
    wb=Workbook();ws=wb.active;ws.append(['工号','姓名','部门','职位','入职日期'])
    for row in [('MS002','张三',ds[0]['name'],'人事负责人','2026-01-01'),('MS002','重复',ds[0]['name'],'人事负责人','2026-01-01'),('MS004','坏行','第五部门','人事负责人','2026-01-01'),('MS003','张三',ds[0]['name'],'人事负责人','2026-01-01')]:ws.append(row)
    out=BytesIO();wb.save(out)
    r=client.post('/api/employees/import',files={'file':('员工.xlsx',out.getvalue())})
    assert r.status_code==200,r.text
    assert r.json()['success_count']==2
    assert r.json()['data'][3]['username']=='张三-MS003'
    assert client.get('/api/employees/export').status_code==200
    login(client,'张三')
    for path in ['/api/employees','/api/employees/export','/api/admin/users']:
        assert client.get(path).status_code==403
    login(client,'admin','Admin123')
    assert client.post('/api/employees',json=employee_body(hr,'MS005')).status_code==403
