from datetime import datetime, timezone
from sqlalchemy import select, update, delete
from app.models import Employee, User, Position, Department, LoginSession, AuditLog, DepartmentSupervisor
from app.core.security import password_hash
from app.core.errors import fail

def audit(db, actor, action, target, identifier, summary=''):
    db.add(AuditLog(actor_user_id=actor.id,action=action,target_type=target,target_id=identifier,summary=summary))

def revoke(db,user_id):
    db.execute(update(LoginSession).where(LoginSession.user_id==user_id).values(revoked_at=datetime.now(timezone.utc)))

def unassign(db,user_id):
    db.execute(delete(DepartmentSupervisor).where(DepartmentSupervisor.user_id==user_id))

def available_hr(db):
    return db.scalar(select(User.id).join(Employee,User.employee_id==Employee.id).where(User.role=='HR',User.is_active==True,Employee.status=='active')) is not None

def unique_username(db,name,number):
    root=name.strip()
    candidate=root
    i=0
    while db.scalar(select(User.id).where(User.username==candidate)):
        i+=1
        suffix=f'-{number}'+(f'-{i}' if i>1 else '')
        candidate=root[:50-len(suffix)]+suffix
    return candidate

def create_employee(db,body,role='EMPLOYEE'):
    if db.scalar(select(Employee.id).where(Employee.employee_no==body.employee_no)):
        fail(409,'EMPLOYEE_EXISTS','工号已存在，不覆盖既有员工或账号')
    pos=db.get(Position,body.position_id)
    if not db.get(Department,body.department_id) or not pos or pos.department_id!=body.department_id or not pos.is_active:
        fail(422,'INVALID_POSITION','请选择所属部门的有效职位')
    employee=Employee(employee_no=body.employee_no,full_name=body.name,department_id=body.department_id,position_id=body.position_id,hire_date=body.hire_date,phone=body.phone,remark=body.remarks,base_salary_cents=int(body.base_salary*100))
    db.add(employee);db.flush()
    user=User(username=unique_username(db,body.name,body.employee_no),password_hash=password_hash.hash('Aa123'),role=role,employee_id=employee.id,display_name=body.name)
    db.add(user);db.flush()
    return employee,user

def employee_view(db,e,limited=False):
    pos=db.get(Position,e.position_id)
    result=dict(id=e.id,employee_no=e.employee_no,name=e.full_name,department_id=e.department_id,department_name=db.get(Department,e.department_id).name,position_id=e.position_id,position_name=pos.name,grade=pos.grade,hire_date=e.hire_date,status='ACTIVE' if e.status=='active' else 'LEFT')
    if not limited:
        account=db.scalar(select(User).where(User.employee_id==e.id))
        from decimal import Decimal
        result.update(phone=e.phone,remarks=e.remark,left_date=e.resignation_date,account_username=account.username if account else None,base_salary=f'{Decimal(e.base_salary_cents)/100:.2f}')
    return result

def user_view(db,u):
    e=db.get(Employee,u.employee_id) if u.employee_id else None
    return dict(id=u.id,username=u.username,role=u.role,employee_id=u.employee_id,is_active=u.is_active,disabled_reason=u.disabled_reason,last_login_at=u.last_login_at,name=e.full_name if e else None,employee_no=e.employee_no if e else None,department_id=e.department_id if e else None,department_name=db.get(Department,e.department_id).name if e else None,employment_status=('ACTIVE' if e.status=='active' else 'LEFT') if e else None,left_date=e.resignation_date if e else None)

def page(query,db,page=1,page_size=50,view=None):
    from sqlalchemy import func
    total=db.scalar(select(func.count()).select_from(query.subquery()))
    rows=db.scalars(query.offset((page-1)*page_size).limit(page_size)).all()
    return {'data':[view(r) if view else r for r in rows],'total':total}
