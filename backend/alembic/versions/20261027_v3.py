"""Upgrade V3 roles and history without losing employee or business records."""
from alembic import op
import sqlalchemy as sa
from app.core.database import Base
from app import models

revision='20261027_03'
down_revision='20261027_01'

def upgrade():
    bind=op.get_bind()
    columns=lambda table:{c['name'] for c in sa.inspect(bind).get_columns(table)}
    checks=sa.inspect(bind).get_check_constraints('users')
    if any('ADMIN' in c['sqltext'] and 'SYS_ADMIN' not in c['sqltext'] for c in checks):
        with op.batch_alter_table('users',recreate='always') as batch:
            batch.drop_constraint('user_role_valid',type_='check')
        bind.exec_driver_sql("UPDATE users SET role='SYS_ADMIN' WHERE role IN ('ADMIN','admin')")
        with op.batch_alter_table('users',recreate='always') as batch:
            batch.create_check_constraint('user_role_valid',"role IN ('SYS_ADMIN','EMPLOYEE','SUPERVISOR','HR')")
    for table, additions in {
        'users':[sa.Column('disabled_reason',sa.String),sa.Column('last_login_at',sa.DateTime)],
        'positions':[sa.Column('grade',sa.String,nullable=False,server_default='L1')],
        'leave_requests':[sa.Column('department_id_at_apply',sa.Integer),sa.Column('review_note',sa.String)],
    }.items():
        for column in additions:
            if column.name not in columns(table):op.add_column(table,column)
    bind.exec_driver_sql('UPDATE leave_requests SET department_id_at_apply=(SELECT department_id FROM employees WHERE employees.id=leave_requests.employee_id) WHERE department_id_at_apply IS NULL')
    Base.metadata.create_all(bind)
    fixed=[('PRODUCTION','制琴生产部'),('QUALITY','质量检验部'),('SALES','销售部'),('WAREHOUSE_PURCHASE','仓储采购部')]
    has_legacy_departments=bool(bind.execute(sa.text('SELECT count(*) FROM departments')).scalar())
    for code,name in fixed:
        if has_legacy_departments and not bind.execute(sa.text('SELECT id FROM departments WHERE name=:name'),{'name':name}).first():
            bind.execute(sa.text('INSERT INTO departments(code,name,is_active,created_at) VALUES(:code,:name,1,CURRENT_TIMESTAMP)'),{'code':code,'name':name})
    target=bind.execute(sa.text('SELECT id FROM departments WHERE name=:name'),{'name':fixed[0][1]}).scalar()
    ids=[r[0] for r in bind.execute(sa.text('SELECT id FROM departments WHERE name NOT IN (:a,:b,:c,:d)'),dict(zip('abcd',[r[1] for r in fixed])))]
    for old_id in ids:
        original_name=bind.execute(sa.text('SELECT name FROM departments WHERE id=:id'),{'id':old_id}).scalar()
        actor_id=bind.execute(sa.text('SELECT id FROM users ORDER BY id LIMIT 1')).scalar()
        if actor_id:
            bind.execute(sa.text("INSERT INTO audit_logs(actor_user_id,action,target_type,target_id,summary,created_at) VALUES(:actor,'MIGRATE_DEPARTMENT','departments',:id,:summary,CURRENT_TIMESTAMP)"),{'actor':actor_id,'id':old_id,'summary':f'旧部门 {original_name}（ID {old_id}）合并至制琴生产部；员工与职位ID保留，原库见迁移前备份'})
        for position in bind.execute(sa.text('SELECT id,name FROM positions WHERE department_id=:id'),{'id':old_id}).all():
            bind.execute(sa.text('UPDATE positions SET name=:name,department_id=:target WHERE id=:id'),{'name':f'{position[1]}（原部门{old_id}）','target':target,'id':position[0]})
        bind.execute(sa.text('UPDATE employees SET department_id=:target WHERE department_id=:id'),{'target':target,'id':old_id})
        bind.execute(sa.text('UPDATE leave_requests SET department_id_at_apply=:target WHERE department_id_at_apply=:id'),{'target':target,'id':old_id})
        bind.execute(sa.text('DELETE FROM departments WHERE id=:id'),{'id':old_id})
    for code,name in fixed:
        bind.execute(sa.text('UPDATE departments SET code=:code,is_active=1 WHERE name=:name'),{'code':code,'name':name})
    bind.exec_driver_sql("INSERT INTO salaries(employee_id,year,month,amount) SELECT employee_id,CAST(substr(salary_month,1,4) AS INTEGER),CAST(substr(salary_month,6,2) AS INTEGER),net_salary_cents/100.0 FROM payroll_records WHERE NOT EXISTS (SELECT 1 FROM salaries s WHERE s.employee_id=payroll_records.employee_id AND s.year=CAST(substr(salary_month,1,4) AS INTEGER) AND s.month=CAST(substr(salary_month,6,2) AS INTEGER))")
    bind.exec_driver_sql("INSERT INTO employment_events(employee_id,event_type,event_date,note) SELECT id,'LEFT',resignation_date,'V3历史迁移' FROM employees WHERE status='resigned' AND NOT EXISTS (SELECT 1 FROM employment_events ev WHERE ev.employee_id=employees.id AND ev.event_type='LEFT')")
    bind.exec_driver_sql("UPDATE users SET is_active=0,disabled_reason='EMPLOYEE_LEFT' WHERE employee_id IN (SELECT id FROM employees WHERE status='resigned')")
    bind.exec_driver_sql('UPDATE sessions SET revoked_at=CURRENT_TIMESTAMP')
    # Legacy raw Web punches remain visible in V3 histories and reports.
    from datetime import datetime
    for row in bind.execute(sa.text("SELECT employee_id,attendance_date,clock_in,clock_out FROM attendance_records WHERE source <> 'leave'")):
        for kind,value in [('IN',row.clock_in),('OUT',row.clock_out)]:
            if not value:continue
            try:stamp=datetime.fromisoformat(f'{row.attendance_date}T{value}')
            except ValueError:continue
            if not bind.execute(sa.text('SELECT id FROM punch_records WHERE employee_id=:e AND punch_date=:d AND punch_type=:t'),{'e':row.employee_id,'d':row.attendance_date,'t':kind}).first():
                bind.execute(sa.text('INSERT INTO punch_records(employee_id,punch_date,punch_type,punch_time) VALUES(:e,:d,:t,:v)'),{'e':row.employee_id,'d':row.attendance_date,'t':kind,'v':stamp})
    # Every pre-existing employee also receives exactly one account; existing
    # credentials, employee IDs and explicit usernames are preserved.
    from sqlalchemy.orm import Session
    from app.models import Employee,User
    from app.services.v3 import unique_username
    from app.core.security import password_hash
    with Session(bind=bind) as db:
        for employee in db.scalars(sa.select(Employee).order_by(Employee.id)):
            if not db.scalar(sa.select(User.id).where(User.employee_id==employee.id)):
                db.add(User(username=unique_username(db,employee.full_name,employee.employee_no),password_hash=password_hash.hash('Aa123'),role='EMPLOYEE',employee_id=employee.id,display_name=employee.full_name,is_active=employee.status=='active',disabled_reason='EMPLOYEE_LEFT' if employee.status!='active' else None))
                db.flush()

def downgrade():
    raise RuntimeError('请从迁移前备份恢复，避免丢失业务历史')
