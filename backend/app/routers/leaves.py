from datetime import date,datetime,timezone
from typing import Literal
from fastapi import APIRouter,Depends,Query
from sqlalchemy import select,update
from sqlalchemy.orm import Session
from pydantic import Field,model_validator
from app.core.database import get_db
from app.core.security import require_admin,require_employee
from app.core.errors import fail,commit
from app.models import LeaveRequest,Attendance,Employee,User
from app.schemas import Input
from app.services.common import get,serialize
from app.services.business import working_days,page_result,audit

router=APIRouter(prefix='/api')

class LeaveInput(Input):
    leave_type:Literal['personal','sick','annual']
    start_date:date
    end_date:date
    reason:str=Field(min_length=1,max_length=1000)
    @model_validator(mode='after')
    def dates(self):
        if not working_days(self.start_date,self.end_date):raise ValueError('请假范围至少包含一个工作日')
        return self

class RejectInput(Input):
    rejection_reason:str=Field(min_length=1,max_length=1000)

def leave_view(db,row):
    employee=db.get(Employee,row.employee_id)
    return dict(serialize(row),name=employee.full_name,employee_code=employee.employee_no)

def leave_list(db,user=None,status=None,keyword='',start_date=None,end_date=None,page=1,page_size=10):
    query=select(LeaveRequest).join(Employee)
    if user:query=query.where(LeaveRequest.employee_id==user.employee_id)
    if status:query=query.where(LeaveRequest.status==status)
    if keyword:query=query.where(Employee.full_name.contains(keyword,autoescape=True))
    if start_date:query=query.where(LeaveRequest.end_date>=start_date)
    if end_date:query=query.where(LeaveRequest.start_date<=end_date)
    return page_result(db,query.order_by(LeaveRequest.id.desc()),page,page_size,lambda r:leave_view(db,r))

@router.get('/leaves')
def admin_list(db:Session=Depends(get_db),user:User=Depends(require_admin),status:str|None=None,keyword:str='',start_date:date|None=None,end_date:date|None=None,page:int=Query(1,ge=1),page_size:int=Query(10,ge=1,le=100)):
    return leave_list(db,None,status,keyword,start_date,end_date,page,page_size)

@router.get('/employee/leaves')
def own_list(db:Session=Depends(get_db),user:User=Depends(require_employee),status:str|None=None,page:int=Query(1,ge=1),page_size:int=Query(10,ge=1,le=100)):
    return leave_list(db,user,status,page=page,page_size=page_size)

@router.post('/employee/leaves',status_code=201)
def create(body:LeaveInput,db:Session=Depends(get_db),user:User=Depends(require_employee)):
    obj=LeaveRequest(employee_id=user.employee_id,**body.model_dump());db.add(obj);commit(db)
    return {'data':leave_view(db,obj)}

def pending(db,id):
    obj=get(db,LeaveRequest,id)
    if obj.status!='pending':fail(409,'LEAVE_REVIEWED','申请已处理，不能重复操作')
    return obj

@router.post('/employee/leaves/{id}/cancel')
def cancel(id:int,db:Session=Depends(get_db),user:User=Depends(require_employee)):
    obj=get(db,LeaveRequest,id)
    if obj.employee_id!=user.employee_id:fail(403,'FORBIDDEN','不能撤销其他员工的申请')
    pending(db,id)
    result=db.execute(update(LeaveRequest).where(LeaveRequest.id==id,LeaveRequest.status=='pending').values(status='cancelled'))
    if not result.rowcount:fail(409,'LEAVE_REVIEWED','申请已被处理')
    commit(db);return {'data':leave_view(db,obj)}

@router.post('/leaves/{id}/approve')
def approve(id:int,db:Session=Depends(get_db),user:User=Depends(require_admin)):
    obj=pending(db,id)
    days=working_days(obj.start_date,obj.end_date)
    conflict=db.scalar(select(Attendance.id).where(Attendance.employee_id==obj.employee_id,Attendance.attendance_date.in_(days)).limit(1))
    if conflict:fail(409,'ATTENDANCE_CONFLICT','请假范围已有考勤或已批准请假，请先核对；本次审批未生效')
    result=db.execute(update(LeaveRequest).where(LeaveRequest.id==id,LeaveRequest.status=='pending').values(status='approved',reviewer_user_id=user.id,reviewed_at=datetime.now(timezone.utc)))
    if not result.rowcount:fail(409,'LEAVE_REVIEWED','申请已被处理')
    for day in days:db.add(Attendance(employee_id=obj.employee_id,attendance_date=day,status='leave',source='leave',leave_id=id))
    audit(db,user,'approve','leave',id,'请假审批通过并生成工作日考勤')
    commit(db,'ATTENDANCE_CONFLICT','请假考勤冲突，本次审批已回滚')
    return {'data':leave_view(db,obj)}

@router.post('/leaves/{id}/reject')
def reject(id:int,body:RejectInput,db:Session=Depends(get_db),user:User=Depends(require_admin)):
    obj=pending(db,id)
    result=db.execute(update(LeaveRequest).where(LeaveRequest.id==id,LeaveRequest.status=='pending').values(status='rejected',reviewer_user_id=user.id,reviewed_at=datetime.now(timezone.utc),rejection_reason=body.rejection_reason))
    if not result.rowcount:fail(409,'LEAVE_REVIEWED','申请已被处理')
    audit(db,user,'reject','leave',id,'请假审批驳回');commit(db)
    return {'data':leave_view(db,obj)}
