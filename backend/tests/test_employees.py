import pytest
from sqlalchemy import select, func
from app.models import Employee, Skill, Department, Position
from test_auth import admin, auth

@pytest.fixture
def dictionaries(client, auth):
    def create(path, body):
        return client.post('/api/' + path, headers=auth, json=body).json()['data']['id']
    d1 = create('departments', {'code': 'D1', 'name': '演示木工'})
    d2 = create('departments', {'code': 'D2', 'name': '演示涂装'})
    p1 = create('positions', {'code': 'P1', 'name': '演示木工岗', 'department_id': d1})
    p2 = create('positions', {'code': 'P2', 'name': '演示涂装岗', 'department_id': d2})
    skills = [create('skills', {'code': f'S{i}', 'name': f'演示技能{i}'}) for i in range(1, 3)]
    return d1, d2, p1, p2, skills

@pytest.fixture
def payload(dictionaries):
    d1, _, p1, _, _ = dictionaries
    return {'employee_no': 'MS_TEST', 'full_name': '演示员工乙', 'department_id': d1, 'position_id': p1, 'hire_date': '2026-10-01','phone':'13800000001'}

@pytest.fixture
def employee(client, auth, payload):
    result = client.post('/api/employees', headers=auth, json=payload)
    assert result.status_code == 201, result.text
    return result.json()['data']

def test_create_edit_persist(client, auth, employee, payload, db):
    id = employee['id']
    assert db.get(Employee, id).full_name == payload['full_name']
    duplicate = client.post('/api/employees', headers=auth, json=payload)
    assert duplicate.status_code == 409 and duplicate.json()['error']['code'] == 'EMPLOYEE_NO_EXISTS'
    assert client.patch(f'/api/employees/{id}', headers=auth, json={'employee_no': 'OTHER'}).status_code == 422
    assert client.patch(f'/api/employees/{id}', headers=auth, json={'full_name': '  演示新名  ', 'phone': '13800000002'}).status_code == 200
    assert client.patch(f'/api/employees/{id}',headers=auth,json={'phone':None}).status_code==422
    assert client.get(f'/api/employees/{id}', headers=auth).json()['data']['full_name'] == '演示新名'
    assert 'phone' in client.get('/api/employees',headers=auth).json()['data'][0]

@pytest.mark.parametrize('changes', [{'full_name': ' '}, {'hire_date': '2026-02-30'}, {'department_id': 999}, {'position_id': 999}, {'phone': 'notphone'}, {'full_name': None}])
def test_invalid_employee(client, auth, payload, changes, db):
    assert client.post('/api/employees', headers=auth, json=payload | changes).status_code == 422
    assert db.scalar(select(func.count(Employee.id))) == 0

def test_mismatch_and_disabled_history(client, auth, employee, payload, dictionaries):
    d1, d2, p1, p2, _ = dictionaries
    assert client.post('/api/employees', headers=auth, json=payload | {'position_id': p2}).status_code == 422
    assert client.patch(f'/api/positions/{p1}', headers=auth, json={'department_id': d2}).status_code == 409
    client.patch(f'/api/departments/{d1}', headers=auth, json={'is_active': False})
    client.patch(f'/api/positions/{p1}', headers=auth, json={'is_active': False})
    assert client.post('/api/employees', headers=auth, json=payload | {'employee_no': 'NEW'}).status_code == 422
    assert client.patch(f"/api/employees/{employee['id']}", headers=auth, json={'remark': '保留停用历史'}).status_code == 200
    assert client.patch(f"/api/employees/{employee['id']}", headers=auth, json={'department_id': d2, 'position_id': p2}).status_code == 200

def test_skills_filters_and_pagination(client, auth, employee, dictionaries, db):
    id = employee['id']
    skill1, skill2 = dictionaries[-1]
    for sid in [skill1, skill2]:
        assert client.post(f'/api/employees/{id}/skills', headers=auth, json={'skill_id': sid, 'proficiency': 'basic'}).status_code == 201
    assert client.post(f'/api/employees/{id}/skills', headers=auth, json={'skill_id': skill1, 'proficiency': 'expert'}).status_code == 409
    assert client.patch(f'/api/employees/{id}/skills/{skill1}', headers=auth, json={'proficiency': 'expert'}).status_code == 200
    assert client.patch(f'/api/employees/{id}/skills/{skill1}', headers=auth, json={'proficiency': 'invalid'}).status_code == 422
    assert client.get(f'/api/employees/{id}/skills', headers=auth).json()['data'][0]['proficiency'] == 'expert'
    params = {'keyword': '演示员工', 'department_id': dictionaries[0], 'skill_id': skill1, 'status': 'active', 'page_size': 1}
    assert client.get('/api/employees', headers=auth, params=params).json()['total'] == 1
    assert client.get('/api/employees', headers=auth, params={'keyword': employee['employee_no']}).json()['total'] == 1
    assert client.get('/api/employees', headers=auth, params={'keyword': 'missing'}).json()['data'] == []
    assert client.get('/api/employees', headers=auth, params={'page': 2, 'page_size': 1}).json()['data'] == []
    for params in [{'page': 0}, {'page_size': 101}, {'page_size': 0}, {'status': 'invalid'}]:
        assert client.get('/api/employees', headers=auth, params=params).status_code == 422
    assert client.delete(f'/api/employees/{id}/skills/{skill1}', headers=auth).status_code == 200
    assert db.get(Skill, skill1)
    client.patch(f'/api/skills/{skill1}', headers=auth, json={'is_active': False})
    assert client.post(f'/api/employees/{id}/skills', headers=auth, json={'skill_id': skill1, 'proficiency': 'basic'}).status_code == 422

def test_archive(client, auth, employee, db):
    id = employee['id']
    path = f'/api/employees/{id}/archive'
    assert client.post(path, headers=auth, json={'resignation_date': '2026-09-30'}).status_code == 422
    assert client.post(path, headers=auth, json={'resignation_date': '2026-10-02'}).status_code == 200
    assert client.post(path, headers=auth, json={'resignation_date': '2026-10-02'}).status_code == 409
    assert client.get('/api/employees', headers=auth).json()['total'] == 0
    assert client.get('/api/employees', headers=auth, params={'status': 'resigned'}).json()['total'] == 1
    assert client.get('/api/employees', headers=auth, params={'status': 'all'}).json()['total'] == 1
    assert db.get(Employee, id)
    assert client.patch(f'/api/employees/{id}', headers=auth, json={'hire_date': '2026-10-03'}).status_code == 422

def test_protected(client):
    assert client.get('/api/employees').status_code == 401
