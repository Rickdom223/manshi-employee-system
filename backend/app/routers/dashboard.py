from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import require_admin as current_user
from app.models import Employee, Department
from app.models import Attendance,LeaveRequest,ProductionTask
from datetime import datetime,timedelta,timezone

router = APIRouter(prefix='/api/dashboard', dependencies=[Depends(current_user)])

@router.get('')
def dashboard(db:Session=Depends(get_db)):
    today=datetime.now(timezone(timedelta(hours=8))).date()
    count=lambda model,*filters:db.scalar(select(func.count(model.id)).where(*filters))
    data={'active':count(Employee,Employee.status=='active'),'departments':count(Department,Department.is_active==True),'today_attendance':count(Attendance,Attendance.attendance_date==today,Attendance.status=='normal'),'today_leave':count(Attendance,Attendance.attendance_date==today,Attendance.status=='leave'),'pending_leaves':count(LeaveRequest,LeaveRequest.status=='pending'),'in_progress_tasks':count(ProductionTask,ProductionTask.status=='in_progress')}
    data['department_distribution']=[{'department_id':id,'name':name,'count':number} for id,name,number in db.execute(select(Department.id,Department.name,func.count(Employee.id)).outerjoin(Employee,(Employee.department_id==Department.id)&(Employee.status=='active')).where(Department.is_active==True).group_by(Department.id))]
    data['attendance_trend']=[{'date':(today-timedelta(days=i)).isoformat(),'count':count(Attendance,Attendance.attendance_date==today-timedelta(days=i),Attendance.status=='normal')} for i in range(6,-1,-1)]
    return {'data':data}

@router.get('/summary')
def summary(db: Session = Depends(get_db)):
    total = db.scalar(select(func.count(Employee.id)))
    active = db.scalar(select(func.count(Employee.id)).where(Employee.status == 'active'))
    departments = db.scalar(select(func.count(Department.id)))
    rows = db.execute(select(Department.id, Department.name, func.count(Employee.id)).outerjoin(Employee, (Employee.department_id == Department.id) & (Employee.status == 'active')).group_by(Department.id).order_by(Department.id))
    return {'data': {'total': total, 'active': active, 'resigned': total - active, 'departments': departments, 'department_distribution': [{'department_id': id, 'name': name, 'count': count} for id, name, count in rows]}}
