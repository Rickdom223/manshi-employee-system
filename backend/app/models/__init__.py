from datetime import date, datetime, timezone
from sqlalchemy import String, ForeignKey, UniqueConstraint, CheckConstraint, Numeric
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

def utcnow():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = 'users'
    __table_args__ = (CheckConstraint("role IN ('SYS_ADMIN','EMPLOYEE','SUPERVISOR','HR')", name='user_role_valid'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str]
    role: Mapped[str] = mapped_column(default='EMPLOYEE')
    employee_id: Mapped[int | None] = mapped_column(ForeignKey('employees.id'), unique=True)
    display_name: Mapped[str | None]
    is_active: Mapped[bool] = mapped_column(default=True)
    disabled_reason: Mapped[str | None]
    last_login_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

class Department(Base):
    __tablename__ = 'departments'
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    description: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

class Position(Base):
    __tablename__ = 'positions'
    __table_args__ = (UniqueConstraint('department_id', 'name', 'grade', name='uq_position_department_name_grade'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(50))
    department_id: Mapped[int] = mapped_column(ForeignKey('departments.id'))
    grade: Mapped[str] = mapped_column(default='L1', server_default='L1')
    is_active: Mapped[bool] = mapped_column(default=True)
    description: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

class Skill(Base):
    __tablename__ = 'skills'
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    is_active: Mapped[bool] = mapped_column(default=True)

class Employee(Base):
    __tablename__ = 'employees'
    __table_args__ = (
        CheckConstraint("status IN ('active','resigned')"),
        CheckConstraint("(status='active' AND resignation_date IS NULL) OR (status='resigned' AND resignation_date >= hire_date)"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_no: Mapped[str] = mapped_column(String(20), unique=True)
    full_name: Mapped[str] = mapped_column(String(50), index=True)
    birth_date: Mapped[date | None]
    base_salary_cents: Mapped[int] = mapped_column(default=0, server_default='0')
    phone: Mapped[str | None]
    department_id: Mapped[int] = mapped_column(ForeignKey('departments.id'), index=True)
    position_id: Mapped[int] = mapped_column(ForeignKey('positions.id'))
    hire_date: Mapped[date]
    status: Mapped[str] = mapped_column(default='active', index=True)
    resignation_date: Mapped[date | None]
    remark: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

class EmployeeSkill(Base):
    __tablename__ = 'employee_skills'
    __table_args__ = (UniqueConstraint('employee_id', 'skill_id'), CheckConstraint("proficiency IN ('basic','skilled','expert')"))
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey('employees.id'), index=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey('skills.id'), index=True)
    proficiency: Mapped[str]
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

class LoginSession(Base):
    __tablename__ = 'sessions'
    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[str] = mapped_column(unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    csrf_token_hash: Mapped[str]
    expires_at: Mapped[datetime]
    revoked_at: Mapped[datetime | None]

class Attendance(Base):
    __tablename__ = 'attendance_records'
    __table_args__ = (UniqueConstraint('employee_id', 'attendance_date'), CheckConstraint("status IN ('normal','late','early_leave','absent','leave')"))
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey('employees.id'), index=True)
    attendance_date: Mapped[date] = mapped_column(index=True)
    clock_in: Mapped[str | None]
    clock_out: Mapped[str | None]
    status: Mapped[str]
    source: Mapped[str] = mapped_column(default='manual')
    leave_id: Mapped[int | None] = mapped_column(ForeignKey('leave_requests.id'))

class LeaveRequest(Base):
    __tablename__ = 'leave_requests'
    __table_args__ = (CheckConstraint("status IN ('pending','approved','rejected','cancelled')"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey('employees.id'), index=True)
    department_id_at_apply: Mapped[int] = mapped_column(ForeignKey('departments.id'))
    leave_type: Mapped[str]
    start_date: Mapped[date]
    end_date: Mapped[date]
    reason: Mapped[str]
    status: Mapped[str] = mapped_column(default='pending')
    reviewer_user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'))
    reviewed_at: Mapped[datetime | None]
    rejection_reason: Mapped[str | None]
    review_note: Mapped[str | None]

class Payroll(Base):
    __tablename__ = 'payroll_records'
    __table_args__ = (UniqueConstraint('employee_id', 'salary_month'), CheckConstraint('net_salary_cents >= 0'))
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey('employees.id'), index=True)
    salary_month: Mapped[str] = mapped_column(index=True)
    base_salary_cents: Mapped[int]
    bonus_cents: Mapped[int] = mapped_column(default=0)
    deduction_cents: Mapped[int] = mapped_column(default=0)
    net_salary_cents: Mapped[int]
    status: Mapped[str] = mapped_column(default='unpaid')
    paid_at: Mapped[datetime | None]

class ProductionTask(Base):
    __tablename__ = 'production_tasks'
    __table_args__ = (CheckConstraint('planned_quantity > 0 AND completed_quantity >= 0 AND completed_quantity <= planned_quantity'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    task_code: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]
    guitar_model: Mapped[str]
    planned_quantity: Mapped[int]
    completed_quantity: Mapped[int] = mapped_column(default=0)
    owner_employee_id: Mapped[int] = mapped_column(ForeignKey('employees.id'))
    start_date: Mapped[date]
    due_date: Mapped[date]
    priority: Mapped[str]
    status: Mapped[str] = mapped_column(default='not_started')
    notes: Mapped[str | None]
    completed_at: Mapped[datetime | None]

class TaskMember(Base):
    __tablename__ = 'production_task_members'
    __table_args__ = (UniqueConstraint('task_id', 'employee_id'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey('production_tasks.id'))
    employee_id: Mapped[int] = mapped_column(ForeignKey('employees.id'))

class Inspection(Base):
    __tablename__ = 'quality_inspections'
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey('production_tasks.id'))
    result: Mapped[str]
    notes: Mapped[str | None]
    inspector_user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    inspected_at: Mapped[datetime] = mapped_column(default=utcnow)

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    action: Mapped[str]
    target_type: Mapped[str]
    target_id: Mapped[int]
    summary: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

class NumberSequence(Base):
    __tablename__ = 'number_sequences'
    key: Mapped[str] = mapped_column(primary_key=True)
    value: Mapped[int]

class DepartmentSupervisor(Base):
    __tablename__ = 'department_supervisors'
    department_id: Mapped[int] = mapped_column(ForeignKey('departments.id'), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), unique=True)
    assigned_at: Mapped[datetime] = mapped_column(default=utcnow)

class EmploymentEvent(Base):
    __tablename__ = 'employment_events'
    __table_args__ = (CheckConstraint("event_type IN ('LEFT','REHIRED')"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey('employees.id'), index=True)
    event_type: Mapped[str]
    event_date: Mapped[date]
    note: Mapped[str | None]

class AttendanceRule(Base):
    __tablename__ = 'attendance_rules'
    id: Mapped[int] = mapped_column(primary_key=True)
    effective_date: Mapped[date] = mapped_column(unique=True)
    weekdays: Mapped[str]
    start_time: Mapped[str]
    end_time: Mapped[str]
    late_grace_minutes: Mapped[int]
    early_grace_minutes: Mapped[int]

class PunchRecord(Base):
    __tablename__ = 'punch_records'
    __table_args__ = (UniqueConstraint('employee_id','punch_date','punch_type'), CheckConstraint("punch_type IN ('IN','OUT')"))
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey('employees.id'), index=True)
    punch_date: Mapped[date] = mapped_column(index=True)
    punch_type: Mapped[str]
    punch_time: Mapped[datetime]

class Salary(Base):
    __tablename__ = 'salaries'
    __table_args__ = (UniqueConstraint('employee_id','year','month'), CheckConstraint('amount >= 0 AND month >= 1 AND month <= 12'))
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey('employees.id'), index=True)
    year: Mapped[int]
    month: Mapped[int]
    amount: Mapped[Decimal] = mapped_column(Numeric(12,2))
    remarks: Mapped[str | None]
    entered_by_user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'))

class InitialDataState(Base):
    __tablename__ = 'initial_data_state'
    key: Mapped[str] = mapped_column(primary_key=True)
    source_digest: Mapped[str]
    installed_at: Mapped[datetime] = mapped_column(default=utcnow)
