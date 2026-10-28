from collections import Counter
from decimal import Decimal
from fastapi import APIRouter,Depends
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import require_hr
from app.models import Employee,Department,Position,EmploymentEvent,LeaveRequest,Salary,AttendanceRule,User
from app.services.v3_attendance import business_now,month_range,days,is_workday,employed_on,summary

router=APIRouter(prefix='/api/dashboard')

def month_shift(day,offset):
    number=day.year*12+day.month-1+offset
    return f'{number//12:04d}-{number%12+1:02d}'

def calculate(db,today):
    current=month_shift(today,0);previous=month_shift(today,-1);first,last=month_range(current)
    employees=db.scalars(select(Employee).order_by(Employee.id)).all()
    active=[e for e in employees if e.status=='active']
    department_counts=Counter(e.department_id for e in active)
    grades=Counter(db.get(Position,e.position_id).grade for e in active)
    def attendance(month):
        records=[summary(db,e,month,today) for e in employees]
        actual=sum(r['actual_days'] for r in records)
        denominator=sum(r['expected_days']-r['approved_leave_days'] for r in records)
        return round(actual/denominator*100,2) if denominator else None
    now_rate,previous_rate=attendance(current),attendance(previous)
    rules=db.scalars(select(AttendanceRule).order_by(AttendanceRule.effective_date)).all()
    types=Counter({'事假':0,'病假':0,'年假':0})
    for leave in db.scalars(select(LeaveRequest).where(LeaveRequest.status=='approved',LeaveRequest.start_date<=last,LeaveRequest.end_date>=first)):
        e=db.get(Employee,leave.employee_id)
        events=db.scalars(select(EmploymentEvent).where(EmploymentEvent.employee_id==e.id).order_by(EmploymentEvent.event_date,EmploymentEvent.id)).all()
        types[leave.leave_type]+=sum(is_workday(rules,d) and employed_on(e,events,d) for d in days(max(first,leave.start_date),min(last,leave.end_date)))
    salaries=[]
    for offset in range(-5,1):
        month=month_shift(today,offset);y,m=map(int,month.split('-'))
        amount=sum(db.scalars(select(Salary.amount).where(Salary.year==y,Salary.month==m)),Decimal('0.00'))
        salaries.append(dict(month=month,amount=f'{amount:.2f}'))
    left=db.scalar(select(func.count(func.distinct(EmploymentEvent.employee_id))).where(EmploymentEvent.event_type=='LEFT',EmploymentEvent.event_date>=first,EmploymentEvent.event_date<=last))
    return dict(month=current,active_employees=len(active),departed_this_month=left,departments=[dict(name=d.name,value=department_counts[d.id]) for d in db.scalars(select(Department).order_by(Department.id))],grades=[dict(name=k,value=v) for k,v in sorted(grades.items())],attendance=dict(current=now_rate,previous=previous_rate,difference=round(now_rate-previous_rate,2) if now_rate is not None and previous_rate is not None else None),leave_days=[dict(name=k,value=v) for k,v in types.items()],salaries=salaries,notes='D04不含未来工作日，分母扣除获批请假；D05按当月完整工作日统计。无生效规则日期不判定出勤。')

@router.get('/hr')
def dashboard(user:User=Depends(require_hr),db:Session=Depends(get_db)):
    return {'data':calculate(db,business_now().date())}
