from datetime import date,time,datetime,timezone
from decimal import Decimal
from typing import Literal,Annotated
from pydantic import Field,model_validator
from fastapi import APIRouter,Depends,Query
from sqlalchemy import select,update,or_
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import require_employee,require_hr,require_supervisor
from app.core.errors import fail
from app.models import *
from app.schemas import Input
from app.schemas.v3 import DateInput
from app.routers.v3_people import get_or_404,commit
from app.services.v3 import audit,revoke,unassign,employee_view,page
from app.services.v3_attendance import business_now,summary,month_range,today_punches

router=APIRouter(prefix='/api')
Month=Annotated[str,Query(pattern=r'^\d{4}-(0[1-9]|1[0-2])$')]

class RuleInput(Input):
    effective_date:date
    weekdays:list[int]=Field(min_length=1,max_length=7)
    start_time:time
    end_time:time
    late_grace_minutes:int=Field(0,ge=0,le=240)
    early_grace_minutes:int=Field(0,ge=0,le=240)
    @model_validator(mode='after')
    def valid(self):
        if any(d<0 or d>6 for d in self.weekdays) or len(set(self.weekdays))!=len(self.weekdays) or self.start_time>=self.end_time:raise ValueError('工作日0..6不可重复，且下班时间须晚于上班')
        return self

class LeaveInput(Input):
    leave_type:Literal['事假','病假','年假']
    start_date:date
    end_date:date
    reason:str=Field(min_length=1,max_length=1000)
    @model_validator(mode='after')
    def valid(self):
        if self.end_date<self.start_date or (self.end_date-self.start_date).days>366:raise ValueError('请假日期顺序错误或超过366天')
        return self

class ReviewInput(Input):
    decision:Literal['approve','reject']
    note:str|None=Field(None,max_length=1000)

class SalaryInput(Input):
    employee_id:int=Field(gt=0)
    year:int=Field(ge=2000,le=2100)
    month:int=Field(ge=1,le=12)
    amount:Decimal=Field(ge=0,max_digits=12,decimal_places=2)
    remarks:str|None=Field(None,max_length=1000)

@router.post('/employees/{id}/leave')
def depart(id:int,body:DateInput,actor:User=Depends(require_hr),db:Session=Depends(get_db)):
    e=get_or_404(db,Employee,id)
    if e.status!='active':fail(409,'ALREADY_LEFT','员工已离职')
    latest=db.scalar(select(EmploymentEvent).where(EmploymentEvent.employee_id==id).order_by(EmploymentEvent.event_date.desc(),EmploymentEvent.id.desc()))
    if body.event_date<e.hire_date or (latest and body.event_date<latest.event_date) or body.event_date>business_now().date():fail(422,'INVALID_DATE','离职日期不得早于入职／上次事件或晚于今天')
    u=db.scalar(select(User).where(User.employee_id==id))
    if u and u.role=='SYS_ADMIN':fail(403,'ADMIN_PROTECTED','系统管理员不能通过员工离职流程停用')
    e.status='resigned';e.resignation_date=body.event_date
    if u:
        u.is_active=False;u.disabled_reason='EMPLOYEE_LEFT';unassign(db,u.id);revoke(db,u.id)
    db.add(EmploymentEvent(employee_id=id,event_type='LEFT',event_date=body.event_date,note=body.note))
    audit(db,actor,'EMPLOYEE_LEFT','employees',id);commit(db)
    return {'data':employee_view(db,e)}

@router.post('/employees/{id}/rehire')
def rehire(id:int,body:DateInput,actor:User=Depends(require_hr),db:Session=Depends(get_db)):
    e=get_or_404(db,Employee,id)
    if e.status!='resigned':fail(409,'NOT_LEFT','员工当前在职')
    if body.event_date<e.resignation_date or body.event_date>business_now().date():fail(422,'INVALID_DATE','复职日期须介于离职日期与今天之间')
    e.status='active';e.resignation_date=None
    u=db.scalar(select(User).where(User.employee_id==id))
    if u:
        u.role='EMPLOYEE';u.is_active=False;u.disabled_reason='REHIRE_PENDING_ADMIN';revoke(db,u.id);unassign(db,u.id)
    db.add(EmploymentEvent(employee_id=id,event_type='REHIRED',event_date=body.event_date,note=body.note))
    audit(db,actor,'EMPLOYEE_REHIRED','employees',id);commit(db)
    return {'data':employee_view(db,e),'message':'已复职，原账号仍停用，待管理员核验启用；权限恢复为普通员工'}

def punch(db,user,kind):
    now=business_now();day=now.date()
    existing=db.scalar(select(PunchRecord).where(PunchRecord.employee_id==user.employee_id,PunchRecord.punch_date==day,PunchRecord.punch_type==kind))
    if existing:fail(409,'ALREADY_PUNCHED','今天已完成此类打卡')
    first=db.scalar(select(PunchRecord).where(PunchRecord.employee_id==user.employee_id,PunchRecord.punch_date==day,PunchRecord.punch_type=='IN'))
    if kind=='OUT' and (not first or first.punch_time.replace(tzinfo=None)>=now.replace(tzinfo=None)):fail(409,'PUNCH_IN_REQUIRED','请先完成上班打卡，下班须晚于上班')
    p=PunchRecord(employee_id=user.employee_id,punch_date=day,punch_type=kind,punch_time=now.replace(tzinfo=None));db.add(p);commit(db)
    return {'data':dict(id=p.id,punch_date=day,punch_type=kind,punch_time=p.punch_time)}

@router.post('/me/punch-in')
def punch_in(user:User=Depends(require_employee),db:Session=Depends(get_db)):return punch(db,user,'IN')

@router.post('/me/punch-out')
def punch_out(user:User=Depends(require_employee),db:Session=Depends(get_db)):return punch(db,user,'OUT')

@router.get('/me/attendance')
def attendance(month:Month,user:User=Depends(require_employee),db:Session=Depends(get_db)):
    result=summary(db,db.get(Employee,user.employee_id),month)
    result['today']=today_punches(db,user.employee_id,business_now().date())
    return {'data':result}

@router.get('/attendance/rules')
def rules(actor:User=Depends(require_hr),db:Session=Depends(get_db)):
    return {'data':[dict(id=r.id,effective_date=r.effective_date,weekdays=[int(w) for w in r.weekdays.split(',')],start_time=r.start_time,end_time=r.end_time,late_grace_minutes=r.late_grace_minutes,early_grace_minutes=r.early_grace_minutes) for r in db.scalars(select(AttendanceRule).order_by(AttendanceRule.effective_date.desc()))]}

@router.post('/attendance/rules')
def add_rule(body:RuleInput,actor:User=Depends(require_hr),db:Session=Depends(get_db)):
    if db.scalar(select(AttendanceRule.id).where(AttendanceRule.effective_date==body.effective_date)):fail(409,'RULE_EXISTS','该生效日期已有规则，请选择新的生效日期')
    r=AttendanceRule(**dict(body.model_dump(),weekdays=','.join(map(str,sorted(body.weekdays))),start_time=body.start_time.isoformat(),end_time=body.end_time.isoformat()))
    db.add(r);db.flush();audit(db,actor,'CREATE_ATTENDANCE_RULE','attendance_rules',r.id);commit(db)
    return {'data':{'id':r.id},'message':'已新增规则版本，旧版本保留'}

@router.get('/attendance/monthly')
def monthly(month:Month,department_id:int|None=None,employee_id:int|None=None,page_no:int=Query(1,alias='page',ge=1),page_size:int=Query(50,ge=1,le=100),actor:User=Depends(require_hr),db:Session=Depends(get_db)):
    q=select(Employee).order_by(Employee.id)
    if department_id:q=q.where(Employee.department_id==department_id)
    if employee_id:q=q.where(Employee.id==employee_id)
    return page(q,db,page_no,page_size,lambda e:{k:v for k,v in summary(db,e,month).items() if k!='daily'})

def leave_view(db,l):
    e=db.get(Employee,l.employee_id)
    return dict(id=l.id,employee_id=l.employee_id,name=e.full_name,employee_no=e.employee_no,department_id=l.department_id_at_apply,leave_type=l.leave_type,start_date=l.start_date,end_date=l.end_date,reason=l.reason,status=l.status.upper(),reviewer_user_id=l.reviewer_user_id,reviewed_at=l.reviewed_at,review_note=l.review_note)

@router.post('/me/leaves')
def apply(body:LeaveInput,user:User=Depends(require_employee),db:Session=Depends(get_db)):
    e=db.get(Employee,user.employee_id)
    l=LeaveRequest(**body.model_dump(),employee_id=e.id,department_id_at_apply=e.department_id)
    db.add(l);commit(db)
    return {'data':leave_view(db,l),'message':'请假已提交，待主管审批' if db.get(DepartmentSupervisor,e.department_id) else '该部门尚未配置主管，申请保持待审批'}

@router.get('/me/leaves')
def my_leaves(page_no:int=Query(1,alias='page',ge=1),page_size:int=Query(50,ge=1,le=100),user:User=Depends(require_employee),db:Session=Depends(get_db)):
    return page(select(LeaveRequest).where(LeaveRequest.employee_id==user.employee_id).order_by(LeaveRequest.id.desc()),db,page_no,page_size,lambda l:leave_view(db,l))

@router.post('/me/leaves/{id}/cancel')
def cancel(id:int,user:User=Depends(require_employee),db:Session=Depends(get_db)):
    changed=db.execute(update(LeaveRequest).where(LeaveRequest.id==id,LeaveRequest.employee_id==user.employee_id,LeaveRequest.status=='pending').values(status='cancelled')).rowcount
    if not changed:fail(409,'NOT_PENDING','仅可撤销本人的待审批申请')
    commit(db);return {'data':{'cancelled':True}}

@router.get('/supervisor/leaves')
def supervisor_leaves(status:Literal['PENDING','APPROVED','REJECTED','CANCELLED']|None=None,page_no:int=Query(1,alias='page',ge=1),page_size:int=Query(50,ge=1,le=100),user:User=Depends(require_supervisor),db:Session=Depends(get_db)):
    s=db.scalar(select(DepartmentSupervisor).where(DepartmentSupervisor.user_id==user.id))
    if not s:return {'data':[],'total':0}
    q=select(LeaveRequest).where(LeaveRequest.department_id_at_apply==s.department_id).order_by(LeaveRequest.id.desc())
    if status:q=q.where(LeaveRequest.status==status.lower())
    return page(q,db,page_no,page_size,lambda l:leave_view(db,l))

@router.post('/supervisor/leaves/{id}/review')
def review(id:int,body:ReviewInput,user:User=Depends(require_supervisor),db:Session=Depends(get_db)):
    l=get_or_404(db,LeaveRequest,id);s=db.get(DepartmentSupervisor,l.department_id_at_apply)
    if l.employee_id==user.employee_id or not s or s.user_id!=user.id:fail(403,'FORBIDDEN','仅可审批当前负责部门且非本人的请假')
    # Claim first: conditional UPDATE both serializes concurrent approvals and
    # makes the subsequent overlap check run after the write lock is acquired.
    changed=db.execute(update(LeaveRequest).where(LeaveRequest.id==id,LeaveRequest.status=='pending').values(status='approved' if body.decision=='approve' else 'rejected',reviewer_user_id=user.id,reviewed_at=datetime.now(timezone.utc),review_note=body.note)).rowcount
    if not changed:fail(409,'ALREADY_REVIEWED','申请已处理，请刷新')
    if body.decision=='approve' and db.scalar(select(LeaveRequest.id).where(LeaveRequest.id!=id,LeaveRequest.employee_id==l.employee_id,LeaveRequest.status=='approved',LeaveRequest.start_date<=l.end_date,LeaveRequest.end_date>=l.start_date)):
        db.rollback();fail(409,'OVERLAP','该员工此日期已有获批请假')
    audit(db,user,'REVIEW_LEAVE','leave_requests',id,body.decision);commit(db)
    return {'data':leave_view(db,db.get(LeaveRequest,id))}

@router.get('/hr/leaves')
def hr_leaves(department_id:int|None=None,employee_id:int|None=None,leave_type:str|None=None,status:Literal['PENDING','APPROVED','REJECTED','CANCELLED']|None=None,start_date:date|None=None,end_date:date|None=None,page_no:int=Query(1,alias='page',ge=1),page_size:int=Query(50,ge=1,le=100),user:User=Depends(require_hr),db:Session=Depends(get_db)):
    q=select(LeaveRequest).order_by(LeaveRequest.id.desc())
    for col,val in [(LeaveRequest.department_id_at_apply,department_id),(LeaveRequest.employee_id,employee_id),(LeaveRequest.leave_type,leave_type),(LeaveRequest.status,status.lower() if status else None)]:
        if val is not None:q=q.where(col==val)
    if start_date:q=q.where(LeaveRequest.end_date>=start_date)
    if end_date:q=q.where(LeaveRequest.start_date<=end_date)
    return page(q,db,page_no,page_size,lambda l:leave_view(db,l))

def salary_view(db,s):
    e=db.get(Employee,s.employee_id)
    return dict(id=s.id,employee_id=s.employee_id,employee_no=e.employee_no,name=e.full_name,year=s.year,month=s.month,amount=f'{s.amount:.2f}',remarks=s.remarks)

def salary_query(year,month,employee_id,search):
    q=select(Salary).join(Employee).order_by(Salary.year.desc(),Salary.month.desc(),Salary.id)
    for col,val in [(Salary.year,year),(Salary.month,month),(Salary.employee_id,employee_id)]:
        if val is not None:q=q.where(col==val)
    if search:q=q.where(or_(Employee.full_name.contains(search),Employee.employee_no.contains(search)))
    return q

@router.get('/salaries')
def salaries(year:int|None=Query(None,ge=2000,le=2100),month:int|None=Query(None,ge=1,le=12),employee_id:int|None=None,search:str|None=None,page_no:int=Query(1,alias='page',ge=1),page_size:int=Query(50,ge=1,le=100),user:User=Depends(require_hr),db:Session=Depends(get_db)):
    return page(salary_query(year,month,employee_id,search),db,page_no,page_size,lambda s:salary_view(db,s))

@router.post('/salaries')
def salary_add(body:SalaryInput,user:User=Depends(require_hr),db:Session=Depends(get_db)):
    get_or_404(db,Employee,body.employee_id)
    if db.scalar(select(Salary.id).where(Salary.employee_id==body.employee_id,Salary.year==body.year,Salary.month==body.month)):fail(409,'SALARY_EXISTS','此员工此工资年月已录入，请编辑既有记录')
    s=Salary(**body.model_dump(),entered_by_user_id=user.id);db.add(s);db.flush();audit(db,user,'CREATE_SALARY','salaries',s.id);commit(db)
    return {'data':salary_view(db,s)}

@router.patch('/salaries/{id}')
def salary_edit(id:int,body:SalaryInput,user:User=Depends(require_hr),db:Session=Depends(get_db)):
    s=get_or_404(db,Salary,id);get_or_404(db,Employee,body.employee_id)
    for k,v in body.model_dump().items():setattr(s,k,v)
    audit(db,user,'UPDATE_SALARY','salaries',id);commit(db);return {'data':salary_view(db,s)}

@router.get('/me/salaries')
def my_salaries(year:int|None=Query(None,ge=2000,le=2100),employee_id:int|None=None,page_no:int=Query(1,alias='page',ge=1),page_size:int=Query(50,ge=1,le=100),user:User=Depends(require_employee),db:Session=Depends(get_db)):
    if employee_id is not None and employee_id!=user.employee_id:fail(403,'FORBIDDEN','只能查看本人工资')
    return page(salary_query(year,None,user.employee_id,None),db,page_no,page_size,lambda s:salary_view(db,s))
