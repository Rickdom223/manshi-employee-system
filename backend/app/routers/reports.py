from datetime import datetime,timezone,timedelta
from fastapi import APIRouter,Depends
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import require_admin
from app.core.errors import fail
from app.models import Department,Employee,Payroll,ProductionTask
from app.services.business import month_range,money
from app.routers.attendance import monthly_summary,STATUSES
from app.routers.exports import excel

router=APIRouter(prefix='/api/reports',dependencies=[Depends(require_admin)])
def departments_data(db):
    return [{'department_id':id,'department':name,'active_count':count} for id,name,count in db.execute(select(Department.id,Department.name,func.count(Employee.id)).outerjoin(Employee,(Employee.department_id==Department.id)&(Employee.status=='active')).group_by(Department.id).order_by(Department.id))]

def payroll_data(db,month):
    month_range(month)
    rows=[]
    for department in db.scalars(select(Department).order_by(Department.id)):
        total=db.scalar(select(func.coalesce(func.sum(Payroll.net_salary_cents),0)).join(Employee).where(Employee.department_id==department.id,Payroll.salary_month==month))
        paid=db.scalar(select(func.coalesce(func.sum(Payroll.net_salary_cents),0)).join(Employee).where(Employee.department_id==department.id,Payroll.salary_month==month,Payroll.status=='paid'))
        rows.append({'department':department.name,'generated_total':money(total),'paid_total':money(paid)})
    return rows

def production_data(db,month):
    start,end=month_range(month)
    lo=datetime.combine(start,datetime.min.time(),timezone(timedelta(hours=8))).astimezone(timezone.utc).replace(tzinfo=None)
    hi=datetime.combine(end,datetime.min.time(),timezone(timedelta(hours=8))).astimezone(timezone.utc).replace(tzinfo=None)
    count,quantity=db.execute(select(func.count(ProductionTask.id),func.coalesce(func.sum(ProductionTask.completed_quantity),0)).where(ProductionTask.status=='completed',ProductionTask.completed_at>=lo,ProductionTask.completed_at<hi)).one()
    return [{'month':month,'completed_tasks':count,'completed_quantity':quantity}]

@router.get('/departments')
def departments(db:Session=Depends(get_db)):return {'data':departments_data(db)}
@router.get('/attendance')
def attendance(month:str,db:Session=Depends(get_db)):return {'data':monthly_summary(db,month)}
@router.get('/payroll')
def payroll(month:str,db:Session=Depends(get_db)):return {'data':payroll_data(db,month),'scope':'已生成工资实发金额与已发放实发金额分别统计'}
@router.get('/production')
def production(month:str,db:Session=Depends(get_db)):return {'data':production_data(db,month)}
@router.get('/export')
def export(type:str,month:str,db:Session=Depends(get_db)):
    if type=='departments':
        rows=departments_data(db);return excel(['部门','在职人数'],[[r['department'],r['active_count']] for r in rows],'部门统计')
    if type=='attendance':
        rows=monthly_summary(db,month);return excel(['姓名','部门编号','正常','迟到','早退','缺勤','请假'],[[r['name'],r['department_id']]+[r[s] for s in STATUSES] for r in rows],'考勤统计')
    if type=='payroll':
        rows=payroll_data(db,month);return excel(['部门','已生成工资支出','已发放工资支出'],[[r['department'],r['generated_total'],r['paid_total']] for r in rows],'工资统计')
    if type=='production':
        rows=production_data(db,month);return excel(['月份','完成任务数','完成制作数量'],[[r['month'],r['completed_tasks'],r['completed_quantity']] for r in rows],'制琴任务统计')
    fail(422,'INVALID_REPORT','报表类型无效')
