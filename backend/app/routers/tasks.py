from datetime import date,datetime,timezone
from typing import Literal
from fastapi import APIRouter,Depends,Query
from sqlalchemy import select,delete,update
from sqlalchemy.orm import Session
from pydantic import Field,model_validator
from app.core.database import get_db
from app.core.security import require_admin
from app.core.errors import fail,commit
from app.models import User,Employee,ProductionTask,TaskMember,Inspection
from app.schemas import Input,Name
from app.services.common import get,serialize
from app.services.business import next_code,page_result,audit

router=APIRouter(prefix='/api/tasks',dependencies=[Depends(require_admin)])

class TaskInput(Input):
    name:Name
    guitar_model:Name
    planned_quantity:int=Field(gt=0,le=100000,strict=True)
    completed_quantity:int=Field(default=0,ge=0,strict=True)
    owner_employee_id:int=Field(gt=0)
    participant_ids:list[int]=Field(default_factory=list,max_length=100)
    start_date:date
    due_date:date
    priority:Literal['low','medium','high']='medium'
    notes:str|None=Field(None,max_length=2000)
    @model_validator(mode='after')
    def valid(self):
        if self.completed_quantity>self.planned_quantity:raise ValueError('完成数量不能超过计划')
        if self.due_date<self.start_date:raise ValueError('预计完成日期不能早于开始日期')
        if len(self.participant_ids)!=len(set(self.participant_ids)):raise ValueError('参与员工不能重复')
        return self

class TransitionInput(Input):
    status:Literal['in_progress','pending_qc','completed']

class InspectionInput(Input):
    result:Literal['passed','failed']
    notes:str|None=Field(None,max_length=2000)

def task_view(db,obj):
    result=serialize(obj)
    ids=list(db.scalars(select(TaskMember.employee_id).where(TaskMember.task_id==obj.id)))
    result.update(owner_name=db.get(Employee,obj.owner_employee_id).full_name,participant_ids=ids,participant_names=[db.get(Employee,id).full_name for id in ids],inspections=[serialize(row) for row in db.scalars(select(Inspection).where(Inspection.task_id==obj.id).order_by(Inspection.id))])
    return result

def validate_members(db,body,original=None):
    old_members=set(db.scalars(select(TaskMember.employee_id).where(TaskMember.task_id==original.id))) if original else set()
    for id in set(body.participant_ids+[body.owner_employee_id]):
        employee=db.get(Employee,id)
        retained=original and (id in old_members or id==original.owner_employee_id)
        if not employee or (employee.status!='active' and not retained):fail(422,'INVALID_MEMBER','负责人和新分配的参与人必须是在职员工')

@router.get('')
def listing(db:Session=Depends(get_db),keyword:str='',status:str|None=None,owner_employee_id:int|None=None,guitar_model:str='',page:int=Query(1,ge=1),page_size:int=Query(10,ge=1,le=100)):
    query=select(ProductionTask)
    if keyword:query=query.where(ProductionTask.name.contains(keyword,autoescape=True))
    if status:query=query.where(ProductionTask.status==status)
    if owner_employee_id:query=query.where(ProductionTask.owner_employee_id==owner_employee_id)
    if guitar_model:query=query.where(ProductionTask.guitar_model.contains(guitar_model,autoescape=True))
    return page_result(db,query.order_by(ProductionTask.id.desc()),page,page_size,lambda r:task_view(db,r))

@router.post('',status_code=201)
def create(body:TaskInput,db:Session=Depends(get_db)):
    validate_members(db,body)
    obj=ProductionTask(**body.model_dump(exclude={'participant_ids'}),task_code=next_code(db,ProductionTask,'TASK','task_code'))
    db.add(obj);db.flush()
    for id in body.participant_ids:db.add(TaskMember(task_id=obj.id,employee_id=id))
    commit(db);return {'data':task_view(db,obj)}

@router.get('/{id}')
def detail(id:int,db:Session=Depends(get_db)):
    return {'data':task_view(db,get(db,ProductionTask,id))}

@router.patch('/{id}')
def edit(id:int,body:TaskInput,db:Session=Depends(get_db)):
    obj=get(db,ProductionTask,id)
    if obj.status in {'pending_qc','completed'}:fail(409,'TASK_LOCKED','待质检或已完成任务不能修改生产资料')
    validate_members(db,body,obj)
    for key,value in body.model_dump(exclude={'participant_ids'}).items():setattr(obj,key,value)
    db.execute(delete(TaskMember).where(TaskMember.task_id==id))
    for employee_id in body.participant_ids:db.add(TaskMember(task_id=id,employee_id=employee_id))
    commit(db);return {'data':task_view(db,obj)}

@router.post('/{id}/transition')
def transition(id:int,body:TransitionInput,db:Session=Depends(get_db),user:User=Depends(require_admin)):
    obj=get(db,ProductionTask,id)
    expected={'in_progress':'not_started','pending_qc':'in_progress','completed':'pending_qc'}[body.status]
    if obj.status!=expected:fail(409,'INVALID_TRANSITION','当前状态不允许此操作')
    if body.status in {'pending_qc','completed'} and obj.completed_quantity!=obj.planned_quantity:fail(422,'INCOMPLETE_QUANTITY','完成数量必须等于计划数量')
    if body.status=='completed':
        latest=db.scalar(select(Inspection).where(Inspection.task_id==id).order_by(Inspection.id.desc()).limit(1))
        if not latest or latest.result!='passed':fail(409,'QC_REQUIRED','必须先完成并通过最新一次质检')
    values={'status':body.status}
    if body.status=='completed':values['completed_at']=datetime.now(timezone.utc)
    changed=db.execute(update(ProductionTask).where(ProductionTask.id==id,ProductionTask.status==expected).values(**values))
    if not changed.rowcount:fail(409,'CONCURRENT_CHANGE','任务状态已变化，请刷新')
    audit(db,user,'transition','task',id,'任务状态更新为'+body.status);commit(db)
    return {'data':task_view(db,obj)}

@router.post('/{id}/inspections',status_code=201)
def inspect_task(id:int,body:InspectionInput,db:Session=Depends(get_db),user:User=Depends(require_admin)):
    obj=get(db,ProductionTask,id)
    if obj.status!='pending_qc':fail(409,'INVALID_QC_STATE','只有待质检任务可以录入质检结果')
    if obj.completed_quantity!=obj.planned_quantity:fail(422,'INCOMPLETE_QUANTITY','生产数量尚未完成')
    changed=db.execute(update(ProductionTask).where(ProductionTask.id==id,ProductionTask.status=='pending_qc').values(status='in_progress' if body.result=='failed' else 'pending_qc'))
    if not changed.rowcount:fail(409,'CONCURRENT_CHANGE','任务状态已变化')
    db.add(Inspection(task_id=id,result=body.result,notes=body.notes,inspector_user_id=user.id))
    audit(db,user,'inspect','task',id,'质检'+body.result);commit(db)
    return {'data':task_view(db,obj)}

@router.get('/{id}/inspections')
def inspections(id:int,db:Session=Depends(get_db)):
    get(db,ProductionTask,id)
    return {'data':[serialize(row) for row in db.scalars(select(Inspection).where(Inspection.task_id==id).order_by(Inspection.id))]}
