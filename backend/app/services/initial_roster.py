"""Install the user's approved 30-person baseline exactly once on a pristine DB."""
import hashlib,json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,model_validator
from sqlalchemy import select,func
from app.core.config import BACKEND
from app.models import User,Employee,Department,Position,DepartmentSupervisor,EmploymentEvent,InitialDataState,AuditLog,Salary,PunchRecord,LeaveRequest,AttendanceRule,Attendance,Payroll,ProductionTask
from app.schemas.v3 import EmployeeInput
from app.services.v3 import create_employee
from app.scripts.initialize_v3 import DEPARTMENTS

DEFAULT_ROSTER=BACKEND/'initial_data/employees_20261028.json'
STATE_KEY='approved-employee-roster'

class RosterEmployee(BaseModel):
    model_config=ConfigDict(extra='forbid')
    employee_no:str
    name:str=Field(min_length=1,max_length=50)
    department:str
    position:str=Field(min_length=1,max_length=50)
    grade:str=Field(min_length=1,max_length=50)
    role:Literal['EMPLOYEE','SUPERVISOR','HR']
    phone:str=Field(pattern=r'^\d{11}$')
    base_salary:Decimal=Field(ge=0,max_digits=12,decimal_places=2)
    hire_date:date
    status:Literal['ACTIVE','LEFT']
    is_active:bool
    left_date:date|None
    disabled_reason:str|None
    @model_validator(mode='after')
    def status_consistent(self):
        if self.status=='LEFT':
            if not self.left_date or self.left_date<self.hire_date or self.is_active or self.disabled_reason!='EMPLOYEE_LEFT':raise ValueError('离职员工的日期和账号停用状态不一致')
        elif self.left_date or self.disabled_reason or not self.is_active:raise ValueError('在职初始员工状态不一致')
        return self

def read_roster(path=DEFAULT_ROSTER):
    data=json.loads(Path(path).read_text(encoding='utf-8-sig'))
    records=[RosterEmployee.model_validate(r) for r in data['employees']]
    if [r.employee_no for r in records]!=[str(i) for i in range(1,31)]:raise ValueError('初始工号必须按1至30连续排列，不补零、不改号')
    if len({r.name for r in records})!=30 or len({r.phone for r in records})!=30:raise ValueError('初始姓名和电话必须分别唯一')
    if {r.department for r in records}!={name for _,name in DEPARTMENTS}:raise ValueError('初始数据必须使用规定的四部门')
    if sum(r.status=='ACTIVE' for r in records)!=27 or sum(r.status=='LEFT' for r in records)!=3:raise ValueError('初始人数应为27在职、3离职')
    if sum(r.base_salary for r in records if r.status=='ACTIVE')!=Decimal('222900.00'):raise ValueError('在职月基本工资合计应为222900.00元')
    if [(r.employee_no,r.name) for r in records if r.role=='HR']!=[('1','李名')]:raise ValueError('初始HR应为工号1的李名')
    if {r.department for r in records if r.role=='SUPERVISOR'}!={name for _,name in DEPARTMENTS} or sum(r.role=='SUPERVISOR' for r in records)!=4:raise ValueError('四部门应各有一名主管')
    digest=hashlib.sha256(json.dumps(data,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    return data,records,digest

def roster_summary(db):
    return dict(employees=db.scalar(select(func.count(Employee.id))),active_employees=db.scalar(select(func.count(Employee.id)).where(Employee.status=='active')),departed_employees=db.scalar(select(func.count(Employee.id)).where(Employee.status=='resigned')),accounts=db.scalar(select(func.count(User.id))),system_admins=db.scalar(select(func.count(User.id)).where(User.role=='SYS_ADMIN')),departments=db.scalar(select(func.count(Department.id))),positions=db.scalar(select(func.count(Position.id))),supervisors=db.scalar(select(func.count(DepartmentSupervisor.department_id))),active_monthly_base_salary=f'{Decimal(db.scalar(select(func.sum(Employee.base_salary_cents)).where(Employee.status=="active")) or 0)/100:.2f}')

def install_roster(db,path=DEFAULT_ROSTER):
    data,records,digest=read_roster(path)
    state=db.get(InitialDataState,STATE_KEY)
    if state:
        if state.source_digest!=digest:raise RuntimeError('初始数据文件已变更，请使用显式重建流程；普通启动不覆盖业务数据')
        return dict(roster_summary(db),already_installed=True)
    admins=db.scalars(select(User)).all()
    if len(admins)!=1 or admins[0].username!='admin' or admins[0].role!='SYS_ADMIN' or admins[0].employee_id is not None:raise RuntimeError('存在旧账号，不能把初始数据合并进旧库；请执行 scripts/reset_initial_data.py')
    for model in [Employee,Position,Salary,PunchRecord,LeaveRequest,AttendanceRule,EmploymentEvent,DepartmentSupervisor,Attendance,Payroll,ProductionTask,AuditLog]:
        if db.scalar(select(func.count()).select_from(model)):raise RuntimeError('数据库包含旧业务，必须使用显式重建流程，禁止混合初始化')
    departments={d.name:d for d in db.scalars(select(Department))}
    if set(departments)!={name for _,name in DEPARTMENTS}:raise RuntimeError('初始数据库部门不符合四部门要求')
    positions={}
    try:
        for record in records:
            key=(record.department,record.position,record.grade)
            if key not in positions:
                p=Position(code=f'POS{len(positions)+1:03}',name=record.position,grade=record.grade,department_id=departments[record.department].id)
                db.add(p);db.flush();positions[key]=p
            p=positions[key]
            body=EmployeeInput(employee_no=record.employee_no,name=record.name,department_id=p.department_id,position_id=p.id,hire_date=record.hire_date,phone=record.phone,base_salary=record.base_salary)
            employee,user=create_employee(db,body,record.role)
            if user.username!=record.name:raise RuntimeError('初始员工姓名账号发生意外冲突')
            if record.status=='LEFT':
                employee.status='resigned';employee.resignation_date=record.left_date
                user.is_active=False;user.disabled_reason='EMPLOYEE_LEFT'
                db.add(EmploymentEvent(employee_id=employee.id,event_type='LEFT',event_date=record.left_date,note='用户确认的初始员工数据'))
            if record.role=='SUPERVISOR':db.add(DepartmentSupervisor(department_id=p.department_id,user_id=user.id))
        db.add(InitialDataState(key=STATE_KEY,source_digest=digest))
        db.add(AuditLog(actor_user_id=admins[0].id,action='INITIAL_ROSTER_INSTALLED',target_type='initial_data',target_id=1,summary=f'按用户确认文档初始化30名员工：{data["source_document"]}'))
        db.flush();result=roster_summary(db)
        assert result['employees']==30 and result['accounts']==31 and result['system_admins']==1 and result['supervisors']==4
        db.commit();return dict(result,already_installed=False)
    except Exception:
        db.rollback();raise
