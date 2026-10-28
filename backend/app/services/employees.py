from sqlalchemy import select
from app.models import Department, Position, Skill, EmployeeSkill, User
from app.services.common import serialize
from app.core.errors import fail

def validate_assignment(db, department_id, position_id, original=None):
    department = db.get(Department, department_id)
    position = db.get(Position, position_id)
    if not department or not position or position.department_id != department_id:
        fail(422, 'INVALID_ASSIGNMENT', '部门或岗位不存在，或岗位不属于该部门')
    if (not original or original.department_id != department_id) and not department.is_active:
        fail(422, 'DEPARTMENT_DISABLED', '不能分配到停用部门')
    if (not original or original.position_id != position_id) and (not position.is_active or not department.is_active):
        fail(422, 'POSITION_DISABLED', '不能分配到停用岗位或部门')

def employee_skills(db, id):
    rows = db.execute(select(EmployeeSkill, Skill).join(Skill, Skill.id == EmployeeSkill.skill_id).where(EmployeeSkill.employee_id == id).order_by(Skill.id))
    return [dict(serialize(link), skill_name=skill.name, skill_code=skill.code, is_active=skill.is_active) for link, skill in rows]

def employee_view(db, obj, detail=False):
    result = serialize(obj)
    from app.services.business import money
    result.update(employee_code=obj.employee_no,name=obj.full_name,base_salary=money(obj.base_salary_cents),departure_date=obj.resignation_date)
    from datetime import datetime,timedelta,timezone
    today=datetime.now(timezone(timedelta(hours=8))).date()
    result['age']=today.year-obj.birth_date.year-((today.month,today.day)<(obj.birth_date.month,obj.birth_date.day)) if obj.birth_date else None
    result['status'] = 'left' if obj.status == 'resigned' else obj.status
    account = db.scalar(select(User).where(User.employee_id==obj.id))
    result['account_username'] = account.username if account else None
    result['account_active'] = account.is_active if account else False
    result['department_name'] = db.get(Department, obj.department_id).name
    result['position_name'] = db.get(Position, obj.position_id).name
    if detail:
        result['skills'] = employee_skills(db, obj.id)
    return result
