"""Increment existing six-table database without deleting business records."""
from alembic import op
import sqlalchemy as sa
from app.core.database import Base
from app import models
revision = '20261027_01'
down_revision = None

def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'users' in inspector.get_table_names():
        columns = {c['name'] for c in inspector.get_columns('users')}
        if 'employee_id' not in columns:
            # Rebuild users with original IDs and hashes; foreign keys are disabled for this migration only.
            op.create_table('users_upgrade', sa.Column('id', sa.Integer, primary_key=True), sa.Column('username', sa.String(50), nullable=False, unique=True), sa.Column('password_hash', sa.String, nullable=False), sa.Column('role', sa.String, nullable=False), sa.Column('is_active', sa.Boolean, nullable=False), sa.Column('created_at', sa.DateTime, nullable=False), sa.Column('employee_id', sa.Integer, sa.ForeignKey('employees.id'), unique=True), sa.Column('display_name', sa.String), sa.CheckConstraint("role IN ('ADMIN','EMPLOYEE','admin')", name='user_role_valid'))
            bind.exec_driver_sql("INSERT INTO users_upgrade(id,username,password_hash,role,is_active,created_at) SELECT id,username,password_hash,CASE WHEN role='admin' THEN 'ADMIN' ELSE role END,is_active,created_at FROM users")
            op.drop_table('users')
            op.rename_table('users_upgrade', 'users')
        additions = {
            'departments': [sa.Column('description', sa.String)],
            'positions': [sa.Column('description', sa.String)],
            'employees': [sa.Column('gender', sa.String), sa.Column('birth_date', sa.Date), sa.Column('base_salary_cents', sa.Integer, nullable=False, server_default='0')],
        }
        for table, new_columns in additions.items():
            existing = {c['name'] for c in sa.inspect(bind).get_columns(table)}
            for column in new_columns:
                if column.name not in existing:
                    op.add_column(table, column)
    Base.metadata.create_all(bind)

def downgrade():
    raise RuntimeError('为保护新增业务数据，不支持自动回滚；请使用迁移前备份恢复到独立副本')
