from datetime import datetime,timezone
from decimal import Decimal
from pydantic import Field
from fastapi import APIRouter,Depends,Query
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import require_admin,require_employee
from app.core.errors import fail,commit
from app.models import Payroll,Employee,User
from app.schemas import Input
from app.services.common import get,serialize
from app.services.business import cents,money,month_range,page_result,audit

router=APIRouter(prefix='/api')
class GenerateInput(Input):
    salary_month:str
class PayrollInput(Input):
    bonus:Decimal=Field(ge=0,max_digits=12,decimal_places=2)
    deduction:Decimal=Field(ge=0,max_digits=12,decimal_places=2)

def payroll_view(db,row):
    employee=db.get(Employee,row.employee_id)
    return dict(serialize(row),employee_code=employee.employee_no,name=employee.full_name,department_id=employee.department_id,base_salary=money(row.base_salary_cents),bonus=money(row.bonus_cents),deduction=money(row.deduction_cents),net_salary=money(row.net_salary_cents))

def payroll_query(month=None,keyword='',department_id=None,employee_id=None):
    query=select(Payroll).join(Employee)
    if month:month_range(month);query=query.where(Payroll.salary_month==month)
    if keyword:query=query.where(Employee.full_name.contains(keyword,autoescape=True))
    if department_id:query=query.where(Employee.department_id==department_id)
    if employee_id:query=query.where(Payroll.employee_id==employee_id)
    return query.order_by(Payroll.salary_month.desc(),Payroll.id.desc())

@router.post('/payroll/generate')
def generate(body:GenerateInput,db:Session=Depends(get_db),user:User=Depends(require_admin)):
    month_range(body.salary_month);created=0
    for employee in db.scalars(select(Employee).where(Employee.status=='active')):
        result=db.execute(insert(Payroll).values(employee_id=employee.id,salary_month=body.salary_month,base_salary_cents=employee.base_salary_cents,bonus_cents=0,deduction_cents=0,net_salary_cents=employee.base_salary_cents,status='unpaid').on_conflict_do_nothing(index_elements=['employee_id','salary_month']))
        created+=result.rowcount
    audit(db,user,'generate','payroll',0,f'生成{body.salary_month}工资，新增{created}条');commit(db)
    return {'data':{'created':created}}

@router.get('/payroll')
def listing(db:Session=Depends(get_db),user:User=Depends(require_admin),month:str|None=None,keyword:str='',department_id:int|None=None,page:int=Query(1,ge=1),page_size:int=Query(10,ge=1,le=100)):
    return page_result(db,payroll_query(month,keyword,department_id),page,page_size,lambda r:payroll_view(db,r))

@router.get('/employee/payroll')
def own(db:Session=Depends(get_db),user:User=Depends(require_employee),month:str|None=None,page:int=Query(1,ge=1),page_size:int=Query(10,ge=1,le=100)):
    return page_result(db,payroll_query(month,employee_id=user.employee_id),page,page_size,lambda r:payroll_view(db,r))

@router.patch('/payroll/{id}')
def edit(id:int,body:PayrollInput,db:Session=Depends(get_db),user:User=Depends(require_admin)):
    obj=get(db,Payroll,id)
    if obj.status=='paid':fail(409,'PAYROLL_PAID','工资已发放，请先撤回发放状态')
    bonus,deduction=cents(body.bonus),cents(body.deduction)
    net=obj.base_salary_cents+bonus-deduction
    if net<0:fail(422,'NEGATIVE_PAYROLL','实发工资不能为负数，请核对扣款')
    obj.bonus_cents,obj.deduction_cents,obj.net_salary_cents=bonus,deduction,net;commit(db)
    return {'data':payroll_view(db,obj)}

@router.post('/payroll/{id}/mark-paid')
def paid(id:int,db:Session=Depends(get_db),user:User=Depends(require_admin)):
    obj=get(db,Payroll,id)
    if obj.status=='paid':fail(409,'ALREADY_PAID','该工资已标记发放')
    obj.status='paid';obj.paid_at=datetime.now(timezone.utc)
    audit(db,user,'mark-paid','payroll',id,'工资标记已发放');commit(db)
    return {'data':payroll_view(db,obj)}

@router.post('/payroll/{id}/reopen')
def reopen(id:int,db:Session=Depends(get_db),user:User=Depends(require_admin)):
    obj=get(db,Payroll,id)
    if obj.status!='paid':fail(409,'NOT_PAID','工资尚未发放')
    obj.status='unpaid';obj.paid_at=None;audit(db,user,'reopen','payroll',id,'撤回工资发放状态');commit(db)
    return {'data':payroll_view(db,obj)}
