from io import BytesIO
from urllib.parse import quote
from fastapi import APIRouter,Depends,Response
from sqlalchemy import select,or_
from sqlalchemy.orm import Session
from openpyxl import Workbook
from app.core.database import get_db
from app.core.security import require_admin
from app.models import Employee,Department
from app.routers.attendance import monthly_summary,STATUSES
from app.routers.payroll import payroll_query,payroll_view
from app.services.employees import employee_view

router=APIRouter(prefix='/api',dependencies=[Depends(require_admin)])
def excel(headers,rows,title):
    workbook=Workbook();sheet=workbook.active;sheet.title=title[:31]
    sheet.append(headers)
    for row in rows:
        sheet.append([("'"+value if value.startswith(('=','+','-','@')) else value) if isinstance(value,str) else value for value in row])
    sheet.freeze_panes='A2';sheet.auto_filter.ref=sheet.dimensions
    for column in sheet.columns:sheet.column_dimensions[column[0].column_letter].width=20
    output=BytesIO();workbook.save(output)
    return Response(output.getvalue(),media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',headers={'Content-Disposition':f"attachment; filename*=UTF-8''{quote(title+'.xlsx')}"})

@router.get('/employees/export')
def employees(db:Session=Depends(get_db),keyword:str='',department_id:int|None=None,status:str='active',skill_id:int|None=None):
    query=select(Employee)
    if keyword:query=query.where(or_(Employee.full_name.contains(keyword,autoescape=True),Employee.employee_no==keyword))
    if department_id:query=query.where(Employee.department_id==department_id)
    if status!='all':query=query.where(Employee.status==('resigned' if status in {'left','resigned'} else status))
    if skill_id:
        from app.models import EmployeeSkill
        query=query.where(Employee.id.in_(select(EmployeeSkill.employee_id).where(EmployeeSkill.skill_id==skill_id)))
    rows=[employee_view(db,e) for e in db.scalars(query.order_by(Employee.id))]
    return excel(['员工编号','姓名','手机号','部门','岗位','入职日期','状态'],[[r['employee_code'],r['name'],r['phone'],r['department_name'],r['position_name'],r['hire_date'].isoformat(),'在职' if r['status']=='active' else '离职'] for r in rows],'员工信息')

@router.get('/attendance/export')
def attendance(month:str,db:Session=Depends(get_db),employee_id:int|None=None,department_id:int|None=None,keyword:str=''):
    rows=monthly_summary(db,month,employee_id,department_id,keyword)
    return excel(['员工编号','姓名','正常','迟到','早退','缺勤','请假'],[[r['employee_code'],r['name']]+[r[s] for s in STATUSES] for r in rows],'月度考勤')

@router.get('/payroll/export')
def payroll(month:str,db:Session=Depends(get_db),keyword:str='',department_id:int|None=None):
    rows=[payroll_view(db,r) for r in db.scalars(payroll_query(month,keyword,department_id))]
    return excel(['员工编号','姓名','月份','基本工资','奖金','扣款','实发工资','状态'],[[r['employee_code'],r['name'],r['salary_month'],r['base_salary'],r['bonus'],r['deduction'],r['net_salary'],'已发放' if r['status']=='paid' else '未发放'] for r in rows],'月度工资')
