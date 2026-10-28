"""One shared attendance calculation for HR month reports and dashboard D04/D05."""
import os, calendar
from datetime import date,datetime,timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import select
from app.models import AttendanceRule, PunchRecord, EmploymentEvent, LeaveRequest, Employee

def business_now():return datetime.now(ZoneInfo(os.getenv('BUSINESS_TIMEZONE','Asia/Shanghai')))

def month_range(month):
    try:first=date.fromisoformat(month+'-01')
    except ValueError:
        from app.core.errors import fail
        fail(422,'INVALID_MONTH','月份格式应为有效的 YYYY-MM')
    return first,first.replace(day=calendar.monthrange(first.year,first.month)[1])

def days(start,end):
    while start<=end:
        yield start;start+=timedelta(days=1)

def rule_for(rules,day):
    return next((r for r in reversed(rules) if r.effective_date<=day),None)

def is_workday(rules,day):
    r=rule_for(rules,day)
    return bool(r and day.weekday() in [int(w) for w in r.weekdays.split(',')])

def employed_on(employee,events,day):
    if day<employee.hire_date:return False
    employed=True
    for event in events:
        if event.event_date>day:break
        employed=event.event_type=='REHIRED'
    # Compatibility for older records without event history.
    if not events and employee.status=='resigned' and employee.resignation_date and day>=employee.resignation_date:return False
    return employed

def summary(db,e,month,today=None):
    today=today or business_now().date();start,end=month_range(month);end=min(end,today)
    rules=db.scalars(select(AttendanceRule).order_by(AttendanceRule.effective_date)).all()
    events=db.scalars(select(EmploymentEvent).where(EmploymentEvent.employee_id==e.id).order_by(EmploymentEvent.event_date,EmploymentEvent.id)).all()
    leaves=db.scalars(select(LeaveRequest).where(LeaveRequest.employee_id==e.id,LeaveRequest.status=='approved',LeaveRequest.start_date<=end,LeaveRequest.end_date>=start)).all()
    punches=db.scalars(select(PunchRecord).where(PunchRecord.employee_id==e.id,PunchRecord.punch_date>=start,PunchRecord.punch_date<=end)).all()
    by_day={}
    for p in punches:
        by_day.setdefault(p.punch_date,{})[p.punch_type]=p.punch_time
    expected=actual=leave_days=late=early=missing=0;daily=[];unconfigured=0
    for day in days(start,end):
        if not employed_on(e,events,day):continue
        rule=rule_for(rules,day);p=by_day.get(day,{});state=[]
        if not rule:
            unconfigured+=1;state.append('尚未配置规则')
        elif is_workday(rules,day):
            expected+=1
            approved=any(l.start_date<=day<=l.end_date for l in leaves)
            if approved:leave_days+=1;state.append('已批准请假')
            elif 'IN' in p:
                actual+=1
                start_at=datetime.fromisoformat(f'{day}T{rule.start_time}')+timedelta(minutes=rule.late_grace_minutes)
                end_at=datetime.fromisoformat(f'{day}T{rule.end_time}')-timedelta(minutes=rule.early_grace_minutes)
                if p['IN'].replace(tzinfo=None)>start_at:late+=1;state.append('迟到')
                if 'OUT' not in p:missing+=1;state.append('缺下班卡')
                elif p['OUT'].replace(tzinfo=None)<end_at:early+=1;state.append('早退')
                if not state:state.append('正常')
            else:state.append('缺勤')
        else:state.append('非工作日')
        daily.append(dict(date=day,punch_in=p.get('IN'),punch_out=p.get('OUT'),status='、'.join(state)))
    denominator=expected-leave_days
    return dict(employee_id=e.id,employee_no=e.employee_no,name=e.full_name,department_id=e.department_id,month=month,expected_days=expected,actual_days=actual,approved_leave_days=leave_days,absent_days=max(0,denominator-actual),late_count=late,early_count=early,missing_punch_count=missing,attendance_rate=round(actual/denominator*100,2) if denominator else None,unconfigured_days=unconfigured,raw_punch_days=sum(d['punch_in'] is not None for d in daily),daily=daily)

def today_punches(db,employee_id,today):
    records=db.scalars(select(PunchRecord).where(PunchRecord.employee_id==employee_id,PunchRecord.punch_date==today)).all()
    rule=db.scalar(select(AttendanceRule).where(AttendanceRule.effective_date<=today).order_by(AttendanceRule.effective_date.desc()))
    shift=dict(start_time=rule.start_time,end_time=rule.end_time,late_grace_minutes=rule.late_grace_minutes,early_grace_minutes=rule.early_grace_minutes) if rule else None
    return dict(date=today,punch_in=next((p.punch_time for p in records if p.punch_type=='IN'),None),punch_out=next((p.punch_time for p in records if p.punch_type=='OUT'),None),shift=shift)
