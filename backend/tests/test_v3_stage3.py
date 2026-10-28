from datetime import date,datetime
from decimal import Decimal
from sqlalchemy import select,func
from app.models import *
from app.services.v3_attendance import summary
from app.routers.v3_dashboard import calculate
from test_v3_stage1 import setup_hr,employee_body,login

def test_dashboard_real_data_cross_month_rules_employment_and_money(client,db):
    ds,hr=setup_hr(client,db)
    r=client.post('/api/employees',json=employee_body(hr));e=r.json()['data'];eid=e['id']
    # Monday Jan 26 -> Friday Feb 6 includes 5 workdays in each month.
    for effective,start in [('2026-01-01','09:00'),('2026-02-01','10:00')]:
        assert client.post('/api/attendance/rules',json={'effective_date':effective,'weekdays':[0,1,2,3,4],'start_time':start,'end_time':'18:00'}).status_code==200
    db.add(LeaveRequest(employee_id=eid,department_id_at_apply=hr['department_id'],leave_type='年假',start_date=date(2026,1,26),end_date=date(2026,2,6),reason='跨月',status='approved'))
    db.add(LeaveRequest(employee_id=eid,department_id_at_apply=hr['department_id'],leave_type='病假',start_date=date(2026,2,9),end_date=date(2026,2,9),reason='未批准',status='pending'))
    db.add(PunchRecord(employee_id=eid,punch_date=date(2026,2,9),punch_type='IN',punch_time=datetime(2026,2,9,9,30)))
    db.add(PunchRecord(employee_id=eid,punch_date=date(2026,1,20),punch_type='IN',punch_time=datetime(2026,1,20,9,30)))
    db.add(Salary(employee_id=eid,year=2026,month=1,amount=Decimal('0.10')))
    db.add(Salary(employee_id=hr['id'],year=2026,month=1,amount=Decimal('0.20')))
    db.commit()
    jan=summary(db,db.get(Employee,eid),'2026-01',date(2026,2,10));feb=summary(db,db.get(Employee,eid),'2026-02',date(2026,2,10))
    assert jan['approved_leave_days']==5 and jan['late_count']==1
    assert feb['expected_days']==7 and feb['approved_leave_days']==5 and feb['late_count']==0
    assert feb['actual_days']==1 and feb['absent_days']==1 and feb['attendance_rate']==50.0
    data=calculate(db,date(2026,2,10))
    assert data['active_employees']==2
    assert len(data['departments'])==4 and sum(x['value'] for x in data['departments'])==2
    assert data['leave_days']==[{'name':'事假','value':0},{'name':'病假','value':0},{'name':'年假','value':5}]
    assert data['salaries'][-2]['amount']=='0.30' and len(data['salaries'])==6
    assert data['attendance']['current']==round(1/(7*2-5)*100,2)
    assert data['grades']==[{'name':'L3','value':2}]

def test_no_rules_zero_denominator_and_departure_event_dedup(client,db):
    ds,hr=setup_hr(client,db);e=client.post('/api/employees',json=employee_body(hr)).json()['data']
    data=calculate(db,date(2026,10,27));assert data['attendance']['current'] is None
    for event_type,day in [('LEFT',1),('REHIRED',2),('LEFT',3),('REHIRED',4)]:
        db.add(EmploymentEvent(employee_id=e['id'],event_type=event_type,event_date=date(2026,10,day)))
    db.commit();data=calculate(db,date(2026,10,27));assert data['departed_this_month']==1
    db.add(AttendanceRule(effective_date=date(2026,1,1),weekdays='0,1,2,3,4',start_time='09:00',end_time='18:00',late_grace_minutes=0,early_grace_minutes=0));db.commit()
    s=summary(db,db.get(Employee,e['id']),'2026-11',date(2026,10,27));assert s['expected_days']==0 and s['attendance_rate'] is None

def test_approved_leave_excludes_absence_and_punch_double_count(client,db):
    ds,hr=setup_hr(client,db);e=db.get(Employee,hr['id'])
    e.hire_date=date(2026,10,26)
    db.add(AttendanceRule(effective_date=date(2026,10,26),weekdays='0,1,2,3,4',start_time='09:00',end_time='18:00',late_grace_minutes=0,early_grace_minutes=0))
    db.add(LeaveRequest(employee_id=e.id,department_id_at_apply=e.department_id,leave_type='病假',start_date=date(2026,10,26),end_date=date(2026,10,26),reason='就诊',status='approved'))
    db.add(PunchRecord(employee_id=e.id,punch_date=date(2026,10,26),punch_type='IN',punch_time=datetime(2026,10,26,9)))
    db.commit();s=summary(db,e,'2026-10',date(2026,10,26))
    assert s['expected_days']==s['approved_leave_days']==1 and s['actual_days']==s['absent_days']==0 and s['attendance_rate'] is None

def test_cross_department_real_request_denied_and_snapshot(client,db):
    ds,hr=setup_hr(client,db)
    pos=client.post('/api/positions',json={'code':'QC01','name':'质检员','department_id':ds[1]['id'],'grade':'L1'}).json()['data']
    body=employee_body(hr,'MS002','质检主管');body.update(department_id=ds[1]['id'],position_id=pos['id'])
    boss=client.post('/api/employees',json=body).json()['data']
    e=client.post('/api/employees',json=employee_body(hr,'MS003')).json()['data']
    login(client,'张三');lid=client.post('/api/me/leaves',json={'leave_type':'事假','start_date':'2026-11-02','end_date':'2026-11-02','reason':'私事'}).json()['data']['id']
    login(client,'admin','Admin123');uid=db.scalar(select(User.id).where(User.employee_id==boss['id']))
    client.put(f"/api/admin/departments/{ds[1]['id']}/supervisor",json={'user_id':uid})
    login(client,'质检主管');assert client.get('/api/supervisor/leaves').json()['total']==0
    assert client.post(f'/api/supervisor/leaves/{lid}/review',json={'decision':'approve'}).status_code==403
    assert client.get(f"/api/departments/{ds[0]['id']}/employees").status_code==403
    assert client.get(f"/api/employees/{e['id']}").status_code==403

def test_hr_recovery_and_role_session_revocation(client,db):
    ds,hr=setup_hr(client,db);e=client.post('/api/employees',json=employee_body(hr)).json()['data']
    login(client,'张三');token=client.cookies.get('manshi_session')
    login(client,'admin','Admin123');uid=db.scalar(select(User.id).where(User.employee_id==e['id']))
    assert client.patch(f'/api/admin/users/{uid}/role',json={'role':'SUPERVISOR'}).status_code==200
    client.cookies.set('manshi_session',token);assert client.get('/api/auth/me').status_code==401
    client.cookies.clear();login(client,'admin','Admin123')
    hr_uid=db.scalar(select(User.id).where(User.employee_id==hr['id']))
    client.post(f'/api/admin/users/{hr_uid}/disable',json={'reason':'离线维护'})
    assert client.get('/api/bootstrap/status').json()['data']['has_active_hr'] is False
    assert client.post('/api/admin/recover-hr',json={'employee_id':e['id']}).status_code==200
    login(client,'张三');assert client.get('/api/auth/me').json()['data']['role']=='HR'

def test_all_role_password_change_and_admin_protection(client,db):
    ds,hr=setup_hr(client,db)
    for no,name,role in [('MS002','普通同事','EMPLOYEE'),('MS003','主管同事','SUPERVISOR')]:
        e=client.post('/api/employees',json=employee_body(hr,no,name)).json()['data']
        login(client,'admin','Admin123');uid=db.scalar(select(User.id).where(User.employee_id==e['id']))
        client.patch(f'/api/admin/users/{uid}/role',json={'role':role});login(client,name)
        assert client.post('/api/auth/change-password',json={'old_password':'Aa123','new_password':'Xy1','confirm_password':'Xy1'}).status_code==200
        login(client,name,'Xy1');login(client,'李人事')
    assert client.post('/api/auth/change-password',json={'old_password':'Aa123','new_password':'Xy1','confirm_password':'Xy1'}).status_code==200
    from app.core.security import limiter
    limiter.entries.clear()  # This multi-role scenario intentionally logs in >10 times.
    login(client,'admin','Admin123');admin=db.scalar(select(User.id).where(User.role=='SYS_ADMIN'))
    assert client.post(f'/api/admin/users/{admin}/disable',json={'reason':'误操作'}).status_code==403
    assert client.get('/api/dashboard/hr').status_code==403
