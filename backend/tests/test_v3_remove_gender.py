from io import BytesIO
from openpyxl import load_workbook
from sqlalchemy import inspect,select,func
from app.models import Employee
from test_v3_stage1 import setup_hr,employee_body,login

def test_removed_attribute_is_absent_and_no_longer_accepted(client,db):
    _,hr=setup_hr(client,db)
    assert 'gender' not in {c['name'] for c in inspect(db.get_bind()).get_columns('employees')}
    body=employee_body(hr)
    assert client.post('/api/employees',json={**body,'gender':'male'}).status_code==422
    assert db.scalar(select(func.count(Employee.id)))==1
    response=client.post('/api/employees',json=body)
    assert response.status_code==200,response.text
    employee=response.json()['data'];assert 'gender' not in employee
    assert client.patch(f"/api/employees/{employee['id']}",json={'gender':None}).status_code==422
    assert 'gender' not in client.get(f"/api/employees/{employee['id']}").json()['data']
    assert all('gender' not in row for row in client.get('/api/employees').json()['data'])
    for path in ['/api/employees/export','/api/employees/import-template']:
        workbook=load_workbook(BytesIO(client.get(path).content),read_only=True)
        header=next(workbook.active.values)
        assert 'gender' not in header and '性别' not in header
        workbook.close()
    login(client,'张三');assert 'gender' not in client.get('/api/me/employee').json()['data']
