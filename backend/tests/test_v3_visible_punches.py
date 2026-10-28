from datetime import datetime
from app.models import PunchRecord
from test_v3_stage1 import setup_hr,employee_body,login

def test_today_card_raw_days_and_server_time(client,db,monkeypatch):
    _,hr=setup_hr(client,db)
    client.post('/api/employees',json=employee_body(hr))
    import app.routers.v3_business as business
    monkeypatch.setattr(business,'business_now',lambda:datetime(2026,10,28,9,0))
    login(client,'张三')
    result=client.post('/api/me/punch-in',json={'source':'TEST','test_run_id':'forged','punch_time':'2000-01-01'}).json()['data']
    assert 'source' not in result and result['punch_time'].startswith('2026-10-28T09:00:00')
    monkeypatch.setattr(business,'business_now',lambda:datetime(2026,10,28,18,0))
    assert client.post('/api/me/punch-out').status_code==200
    result=client.get('/api/me/attendance?month=2026-10').json()['data']
    assert result['raw_punch_days']==1 and result['expected_days']==0 and result['attendance_rate'] is None
    assert result['today']['date']=='2026-10-28' and result['today']['punch_in'] and result['today']['punch_out']
    assert result['today']['shift'] is None
    past=client.get('/api/me/attendance?month=2026-09').json()['data']
    assert past['daily'] and past['raw_punch_days']==0 and past['today']['punch_in']

def test_two_minute_shift_normal_late_early_missing_and_absent(client,db,monkeypatch):
    _,hr=setup_hr(client,db)
    import app.routers.v3_business as business
    import app.services.v3_attendance as calculation
    clock=[datetime(2026,10,28,9,59,50)]
    monkeypatch.setattr(business,'business_now',lambda:clock[0]);monkeypatch.setattr(calculation,'business_now',lambda:clock[0])
    people={}
    for i,key in enumerate(['normal','late','early','missing','absent'],1):
        name='场景'+key;body=employee_body(hr,'SC'+str(i),name)
        people[key]=client.post('/api/employees',json=body).json()['data']
    rule=client.post('/api/attendance/rules',json={'effective_date':'2026-10-28','weekdays':[0,1,2,3,4],'start_time':'10:00:00','end_time':'10:02:00','late_grace_minutes':0,'early_grace_minutes':0})
    assert rule.status_code==200
    for key in ['normal','early','missing']:
        login(client,people[key]['name']);assert client.post('/api/me/punch-in').status_code==200
    clock[0]=datetime(2026,10,28,10,0,30)
    login(client,people['early']['name']);assert client.post('/api/me/punch-out').status_code==200
    clock[0]=datetime(2026,10,28,10,0,40)
    login(client,people['late']['name']);assert client.post('/api/me/punch-in').status_code==200
    clock[0]=datetime(2026,10,28,10,2,2)
    for key in ['normal','late']:
        login(client,people[key]['name']);assert client.post('/api/me/punch-out').status_code==200
    for key,status in [('normal','正常'),('late','迟到'),('early','早退'),('missing','缺下班卡'),('absent','缺勤')]:
        login(client,people[key]['name']);data=client.get('/api/me/attendance?month=2026-10').json()['data']
        assert next(d for d in data['daily'] if d['date']=='2026-10-28')['status']==status
        assert data['today']['shift']['start_time']=='10:00:00'
