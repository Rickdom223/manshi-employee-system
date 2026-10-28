from fastapi import APIRouter,Depends,Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import require_employee,current_user
from app.core.errors import commit
from app.models import User,Employee
from app.schemas.business import ContactInput
from app.services.employees import employee_view
from app.routers.attendance import attendance_query,attendance_view,monthly_summary
from app.services.business import page_result
from sqlalchemy import select,or_
from app.models import ProductionTask,TaskMember,Inspection
from app.services.common import serialize

router=APIRouter(prefix='/api')

@router.get('/employee/me')
def me(db:Session=Depends(get_db),user:User=Depends(require_employee)):
    return {'data':employee_view(db,db.get(Employee,user.employee_id),True)}

@router.patch('/employee/me')
def contact(body:ContactInput,db:Session=Depends(get_db),user:User=Depends(require_employee)):
    employee=db.get(Employee,user.employee_id);employee.phone=body.phone;commit(db)
    return {'data':employee_view(db,employee,True)}

@router.get('/employee/attendance')
def attendance(db:Session=Depends(get_db),user:User=Depends(require_employee),month:str|None=None,status:str|None=None,page:int=Query(1,ge=1),page_size:int=Query(10,ge=1,le=100)):
    return page_result(db,attendance_query(month=month,employee_id=user.employee_id,status=status),page,page_size,lambda r:attendance_view(db,r))

@router.get('/employee/attendance/monthly')
def monthly(month:str,db:Session=Depends(get_db),user:User=Depends(require_employee)):
    return {'data':monthly_summary(db,month,employee_id=user.employee_id)}

@router.get('/settings/company')
def company(user:User=Depends(current_user)):
    return {'data':{'company_name':'满氏吉他制琴有限公司','system_name':'企业员工管理系统','version':'2.0'}}

@router.get('/employee/tasks')
def tasks(db:Session=Depends(get_db),user:User=Depends(require_employee),page:int=Query(1,ge=1),page_size:int=Query(10,ge=1,le=100)):
    query=select(ProductionTask).where(or_(ProductionTask.owner_employee_id==user.employee_id,ProductionTask.id.in_(select(TaskMember.task_id).where(TaskMember.employee_id==user.employee_id))))
    def view(task):
        row=serialize(task);row['owner_name']=db.get(Employee,task.owner_employee_id).full_name
        row['participant_ids']=list(db.scalars(select(TaskMember.employee_id).where(TaskMember.task_id==task.id)))
        row['inspections']=[serialize(r) for r in db.scalars(select(Inspection).where(Inspection.task_id==task.id).order_by(Inspection.id))]
        return row
    return page_result(db,query.order_by(ProductionTask.id.desc()),page,page_size,view)
