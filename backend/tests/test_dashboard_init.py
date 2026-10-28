from sqlalchemy import select, func
from app.models import User, Employee, Position
from datetime import date
from app.scripts.init_db import initialize
from app.core.security import password_hash
from test_auth import admin, auth
from test_employees import dictionaries, payload, employee

def test_empty_dashboard(client, auth):
    data = client.get('/api/dashboard/summary', headers=auth).json()['data']
    assert data == {'total': 0, 'active': 0, 'resigned': 0, 'departments': 0, 'department_distribution': []}

def test_dashboard_changes(client, auth, employee):
    before = client.get('/api/dashboard/summary', headers=auth).json()['data']
    assert before['total'] == before['active'] == 1
    assert sum(x['count'] for x in before['department_distribution']) == 1
    client.post(f"/api/employees/{employee['id']}/archive", headers=auth, json={'resignation_date': '2026-10-03'})
    after = client.get('/api/dashboard/summary', headers=auth).json()['data']
    assert after['active'] == 0 and after['resigned'] == 1 and after['total'] == 1
    assert sum(x['count'] for x in after['department_distribution']) == 0

def test_initialize_idempotent(db, monkeypatch):
    monkeypatch.setenv('INITIAL_ADMIN_PASSWORD', 'Only-test-password!')
    initialize(db)
    user = db.scalar(select(User))
    hash_before = user.password_hash
    position=db.scalar(select(Position))
    employee=Employee(employee_no='SEED_TEST',full_name='测试初始化保留',department_id=position.department_id,position_id=position.id,hire_date=date(2026,10,1))
    db.add(employee)
    employee.full_name = '保留演示修改'
    db.commit()
    monkeypatch.setenv('INITIAL_ADMIN_PASSWORD', 'changed-test-password!')
    initialize(db)
    assert db.scalar(select(func.count(User.id))) == 1
    assert db.scalar(select(func.count(Employee.id))) == 1
    assert user.password_hash == hash_before and hash_before.startswith('$argon2id$')
    assert employee.full_name == '保留演示修改'

def test_dashboard_protected(client):
    assert client.get('/api/dashboard/summary').status_code == 401
