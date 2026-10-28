from typing import Literal
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import require_admin as current_user
from app.core.errors import fail, commit
from app.models import Employee, EmployeeSkill, Skill, User, LoginSession
from app.schemas import EmployeeCreate, EmployeePatch, Archive, SkillBind, Proficiency, Input
from app.services.common import get, apply
from app.services.employees import validate_assignment, employee_view, employee_skills

router = APIRouter(prefix='/api/employees', dependencies=[Depends(current_user)])

@router.get('')
def employees(db: Session = Depends(get_db), keyword: str = Query('', max_length=50), department_id: int | None = Query(None, gt=0), status: Literal['active', 'resigned', 'left','all'] = 'active', skill_id: int | None = Query(None, gt=0), page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100)):
    query = select(Employee)
    if keyword.strip():
        query = query.where(or_(Employee.full_name.contains(keyword.strip(), autoescape=True), Employee.employee_no == keyword.strip()))
    if department_id is not None:
        query = query.where(Employee.department_id == department_id)
    if status != 'all':
        query = query.where(Employee.status == ('resigned' if status=='left' else status))
    if skill_id is not None:
        query = query.where(Employee.id.in_(select(EmployeeSkill.employee_id).where(EmployeeSkill.skill_id == skill_id)))
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.scalars(query.order_by(Employee.id.desc()).offset((page-1)*page_size).limit(page_size))
    return {'data': [employee_view(db, row) for row in rows], 'total': total, 'page': page, 'page_size': page_size}

@router.post('', status_code=201)
def create_employee(body: EmployeeCreate, db: Session = Depends(get_db)):
    validate_assignment(db, body.department_id, body.position_id)
    from app.services.business import next_code,cents
    values=body.model_dump(exclude={'base_salary','create_account','initial_password'})
    if not values['employee_no']:
        values['employee_no']=next_code(db,Employee,'MS','employee_no')
    if not body.phone:
        fail(422,'PHONE_REQUIRED','请填写手机号')
    import re
    if not re.fullmatch(r'1[3-9]\d{9}',body.phone):
        fail(422,'INVALID_PHONE','请输入有效的11位手机号')
    employee = Employee(**values,base_salary_cents=cents(body.base_salary))
    db.add(employee)
    if body.create_account:
        from app.routers.auth import valid_password
        from app.core.security import password_hash
        valid_password(body.initial_password or '')
        from sqlalchemy.exc import IntegrityError
        try:db.flush()
        except IntegrityError:
            db.rollback();fail(409,'EMPLOYEE_NO_EXISTS','工号已存在')
        username=employee.employee_no if len(employee.employee_no)<=10 else f'U{employee.id:06d}'
        db.add(User(username=username,employee_id=employee.id,role='EMPLOYEE',password_hash=password_hash.hash(body.initial_password)))
    commit(db, 'EMPLOYEE_NO_EXISTS', '工号已存在')
    return {'data': employee_view(db, employee, True)}

@router.get('/{id}')
def employee_detail(id: int, db: Session = Depends(get_db)):
    return {'data': employee_view(db, get(db, Employee, id), True)}

@router.patch('/{id}')
def update_employee(id: int, body: EmployeePatch, db: Session = Depends(get_db)):
    employee = get(db, Employee, id)
    values = body.model_dump(exclude_unset=True)
    if 'phone' in values:
        import re
        if values['phone'] != employee.phone and (not values['phone'] or not re.fullmatch(r'1[3-9]\d{9}',values['phone'])):
            fail(422,'INVALID_PHONE','新填写的手机号须为有效11位号码，不能清空')
    if 'base_salary' in values:
        from app.services.business import cents
        employee.base_salary_cents=cents(values.pop('base_salary'))
    validate_assignment(db, values.get('department_id', employee.department_id), values.get('position_id', employee.position_id), employee)
    if employee.resignation_date and values.get('hire_date', employee.hire_date) > employee.resignation_date:
        fail(422, 'INVALID_DATE', '入职日期不能晚于离职日期')
    for key,value in values.items():
        setattr(employee,key,value)
    commit(db)
    return {'data': employee_view(db, employee, True)}

@router.post('/{id}/archive')
def archive_employee(id: int, body: Archive, db: Session = Depends(get_db)):
    employee = get(db, Employee, id)
    if employee.status == 'resigned':
        fail(409, 'ALREADY_ARCHIVED', '员工已归档')
    if body.resignation_date < employee.hire_date:
        fail(422, 'INVALID_DATE', '离职日期不能早于入职日期')
    employee.status, employee.resignation_date = 'resigned', body.resignation_date
    from sqlalchemy import update
    from datetime import datetime,timezone
    users=db.scalars(select(User).where(User.employee_id==id)).all()
    for user in users:
        user.is_active=False
        db.execute(update(LoginSession).where(LoginSession.user_id==user.id).values(revoked_at=datetime.now(timezone.utc)))
    commit(db)
    return {'data': employee_view(db, employee, True)}

@router.get('/{id}/skills')
def skills(id: int, db: Session = Depends(get_db)):
    get(db, Employee, id)
    return {'data': employee_skills(db, id)}

@router.post('/{id}/skills', status_code=201)
def bind_skill(id: int, body: SkillBind, db: Session = Depends(get_db)):
    get(db, Employee, id)
    existing = db.scalar(select(EmployeeSkill).where(EmployeeSkill.employee_id == id, EmployeeSkill.skill_id == body.skill_id))
    if existing:
        fail(409, 'SKILL_ALREADY_BOUND', '员工已关联该技能')
    skill = db.get(Skill, body.skill_id)
    if not skill or not skill.is_active:
        fail(422, 'INVALID_SKILL', '请选择启用的技能')
    db.add(EmployeeSkill(employee_id=id, **body.model_dump()))
    commit(db, 'SKILL_ALREADY_BOUND', '员工已关联该技能')
    return {'data': employee_skills(db, id)}

def get_link(db, id, skill_id):
    get(db, Employee, id)
    link = db.scalar(select(EmployeeSkill).where(EmployeeSkill.employee_id == id, EmployeeSkill.skill_id == skill_id))
    if not link:
        fail(404, 'NOT_FOUND', '技能关联不存在')
    return link

@router.patch('/{id}/skills/{skill_id}')
def change_skill(id: int, skill_id: int, body: Proficiency, db: Session = Depends(get_db)):
    link = get_link(db, id, skill_id)
    link.proficiency = body.proficiency
    commit(db)
    return {'data': employee_skills(db, id)}

@router.delete('/{id}/skills/{skill_id}')
def remove_skill(id: int, skill_id: int, db: Session = Depends(get_db)):
    db.delete(get_link(db, id, skill_id))
    commit(db)
    return {'data': {'removed': True}}

@router.post('/{id}/leave-company')
def leave_company(id:int,body:Archive,db:Session=Depends(get_db)):
    return archive_employee(id,body,db)

class AccountInput(Input):
    initial_password: str

@router.post('/{id}/enable-account')
def enable_account(id:int,body:AccountInput,db:Session=Depends(get_db)):
    employee=get(db,Employee,id)
    if employee.status!='active':
        fail(422,'EMPLOYEE_LEFT','离职员工不能开通账号')
    from app.routers.auth import valid_password
    from app.core.security import password_hash
    valid_password(body.initial_password)
    user=db.scalar(select(User).where(User.employee_id==id))
    if user and user.is_active:
        fail(409,'ACCOUNT_EXISTS','该员工已有有效账号')
    if not user:
        username=employee.employee_no if len(employee.employee_no)<=10 else f'U{id:06d}'
        user=User(username=username,employee_id=id,role='EMPLOYEE',password_hash=password_hash.hash(body.initial_password)); db.add(user)
    else:
        user.password_hash=password_hash.hash(body.initial_password);user.is_active=True
    commit(db)
    return {'data':{'username':user.username}}

@router.post('/{id}/reset-password')
def reset_password(id:int,body:AccountInput,db:Session=Depends(get_db)):
    employee=get(db,Employee,id)
    user=db.scalar(select(User).where(User.employee_id==id))
    if employee.status!='active' or not user:
        fail(422,'ACCOUNT_UNAVAILABLE','仅可重置在职员工已有账号')
    from app.routers.auth import valid_password
    from app.core.security import password_hash
    from sqlalchemy import update
    from datetime import datetime,timezone
    valid_password(body.initial_password)
    user.password_hash=password_hash.hash(body.initial_password)
    db.execute(update(LoginSession).where(LoginSession.user_id==user.id).values(revoked_at=datetime.now(timezone.utc)))
    commit(db)
    return {'data':{'reset':True}}
