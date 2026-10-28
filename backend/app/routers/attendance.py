from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import require_admin
from app.core.errors import fail,commit
from app.models import Employee,Attendance
from app.schemas.business import AttendanceInput
from app.services.common import get,serialize
from app.services.business import month_range,page_result

router=APIRouter(prefix='/api/attendance',dependencies=[Depends(require_admin)])
STATUSES=['normal','late','early_leave','absent','leave']

def attendance_query(month=None,keyword='',department_id=None,employee_id=None,status=None,attendance_date=None):
    query=select(Attendance).join(Employee)
    if month:
        start,end=month_range(month);query=query.where(Attendance.attendance_date>=start,Attendance.attendance_date<end)
    if keyword:query=query.where(Employee.full_name.contains(keyword,autoescape=True))
    if department_id:query=query.where(Employee.department_id==department_id)
    if employee_id:query=query.where(Attendance.employee_id==employee_id)
    if status:query=query.where(Attendance.status==status)
    if attendance_date:query=query.where(Attendance.attendance_date==attendance_date)
    return query.order_by(Attendance.attendance_date.desc(),Attendance.id.desc())

def attendance_view(db,row):
    employee=db.get(Employee,row.employee_id)
    return dict(serialize(row),employee_code=employee.employee_no,name=employee.full_name,department_id=employee.department_id)

def monthly_summary(db,month,employee_id=None,department_id=None,keyword=''):
    start,end=month_range(month)
    employees=select(Employee)
    if employee_id:employees=employees.where(Employee.id==employee_id)
    if department_id:employees=employees.where(Employee.department_id==department_id)
    if keyword:employees=employees.where(Employee.full_name.contains(keyword,autoescape=True))
    result=[]
    for employee in db.scalars(employees.order_by(Employee.id)):
        counts=dict(db.execute(select(Attendance.status,func.count()).where(Attendance.employee_id==employee.id,Attendance.attendance_date>=start,Attendance.attendance_date<end).group_by(Attendance.status)).all())
        result.append(dict(employee_id=employee.id,name=employee.full_name,employee_code=employee.employee_no,department_id=employee.department_id,**{s:counts.get(s,0) for s in STATUSES}))
    return result

@router.get('')
def listing(db:Session=Depends(get_db),month:str|None=None,keyword:str='',department_id:int|None=None,employee_id:int|None=None,status:str|None=None,attendance_date:date|None=None,page:int=Query(1,ge=1),page_size:int=Query(10,ge=1,le=100)):
    return page_result(db,attendance_query(month,keyword,department_id,employee_id,status,attendance_date),page,page_size,lambda r:attendance_view(db,r))

@router.get('/monthly')
def monthly(month:str,db:Session=Depends(get_db),employee_id:int|None=None,department_id:int|None=None,keyword:str=''):
    return {'data':monthly_summary(db,month,employee_id,department_id,keyword)}

def save_attendance(db,body,obj=None):
    employee=get(db,Employee,body.employee_id)
    if not obj and employee.status!='active':fail(422,'EMPLOYEE_LEFT','不能给离职员工新增考勤')
    if obj and obj.source=='leave':fail(409,'LEAVE_ATTENDANCE_LOCKED','审批产生的考勤不能直接修改，请先处理请假业务')
    values=body.model_dump()
    for field in ['clock_in','clock_out']:
        values[field]=values[field].isoformat() if values[field] else None
    if obj:
        for key,value in values.items():setattr(obj,key,value)
    else:obj=Attendance(**values,source='manual');db.add(obj)
    commit(db,'ATTENDANCE_EXISTS','同一员工同一天已有考勤记录')
    return {'data':attendance_view(db,obj)}

@router.post('',status_code=201)
def create(body:AttendanceInput,db:Session=Depends(get_db)):
    return save_attendance(db,body)

@router.patch('/{id}')
def update_record(id:int,body:AttendanceInput,db:Session=Depends(get_db)):
    return save_attendance(db,body,get(db,Attendance,id))
