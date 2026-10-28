from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import require_admin as current_user
from app.core.errors import fail, commit
from app.models import Department, Position, Skill, Employee
from app.schemas import DictionaryCreate, DictionaryPatch, PositionCreate, PositionPatch
from app.services.common import get, serialize, apply

router = APIRouter(prefix='/api', dependencies=[Depends(current_user)])

def list_dictionary(model, db, page, page_size, is_active=None, department_id=None):
    query = select(model)
    if is_active is not None:
        query = query.where(model.is_active == is_active)
    if department_id is not None:
        query = query.where(model.department_id == department_id)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.scalars(query.order_by(model.id).offset((page-1)*page_size).limit(page_size)).all()
    return {'data': [serialize(row) for row in rows], 'total': total, 'page': page, 'page_size': page_size}

def create_dictionary(model, body, db):
    from app.services.business import next_code
    values = body.model_dump()
    if not values.get('code'):
        values['code'] = next_code(db, model, {Department:'DEP',Position:'POS',Skill:'SK'}[model])
    if model is Skill:
        values.pop('description',None)
    obj = model(**values)
    db.add(obj)
    commit(db)
    return {'data': serialize(obj)}

def update_dictionary(model, id, body, db):
    obj = get(db, model, id)
    apply(obj, body)
    commit(db)
    return {'data': serialize(obj)}

@router.get('/departments')
def departments(db: Session = Depends(get_db), page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100), is_active: bool | None = None):
    result = list_dictionary(Department, db, page, page_size, is_active)
    for row in result['data']:
        row['department_code']=row['code']
        row['employee_count']=db.scalar(select(func.count(Employee.id)).where(Employee.department_id==row['id'],Employee.status=='active'))
    return result

@router.post('/departments', status_code=201)
def department_create(body: DictionaryCreate, db: Session = Depends(get_db)):
    return create_dictionary(Department, body, db)

@router.patch('/departments/{id}')
def department_update(id: int, body: DictionaryPatch, db: Session = Depends(get_db)):
    return update_dictionary(Department, id, body, db)

@router.get('/positions')
def positions(db: Session = Depends(get_db), page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100), is_active: bool | None = None, department_id: int | None = Query(None, gt=0)):
    return list_dictionary(Position, db, page, page_size, is_active, department_id)

def check_department(db, id):
    department = db.get(Department, id)
    if not department or not department.is_active:
        fail(422, 'INVALID_DEPARTMENT', '请选择启用的部门')

@router.post('/positions', status_code=201)
def position_create(body: PositionCreate, db: Session = Depends(get_db)):
    check_department(db, body.department_id)
    return create_dictionary(Position, body, db)

@router.patch('/positions/{id}')
def position_update(id: int, body: PositionPatch, db: Session = Depends(get_db)):
    position = get(db, Position, id)
    if body.department_id is not None and body.department_id != position.department_id:
        check_department(db, body.department_id)
        if db.scalar(select(Employee.id).where(Employee.position_id == id).limit(1)):
            fail(409, 'POSITION_IN_USE', '岗位已被员工引用，不能变更所属部门，请新增岗位')
    return update_dictionary(Position, id, body, db)

@router.get('/skills')
def skills(db: Session = Depends(get_db), page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100), is_active: bool | None = None):
    return list_dictionary(Skill, db, page, page_size, is_active)

@router.post('/skills', status_code=201)
def skill_create(body: DictionaryCreate, db: Session = Depends(get_db)):
    return create_dictionary(Skill, body, db)

@router.patch('/skills/{id}')
def skill_update(id: int, body: DictionaryPatch, db: Session = Depends(get_db)):
    return update_dictionary(Skill, id, body, db)

@router.delete('/departments/{id}')
def department_delete(id: int, db: Session=Depends(get_db)):
    obj=get(db,Department,id)
    if db.scalar(select(Employee.id).where(Employee.department_id==id).limit(1)) or db.scalar(select(Position.id).where(Position.department_id==id).limit(1)):
        fail(409,'DEPARTMENT_IN_USE','部门存在员工或岗位关联，不能删除')
    db.delete(obj); commit(db)
    return {'data':{'deleted':True}}

@router.delete('/positions/{id}')
def position_delete(id: int, db: Session=Depends(get_db)):
    obj=get(db,Position,id)
    if db.scalar(select(Employee.id).where(Employee.position_id==id).limit(1)):
        fail(409,'POSITION_IN_USE','岗位存在员工历史关联，不能删除')
    db.delete(obj); commit(db)
    return {'data':{'deleted':True}}
