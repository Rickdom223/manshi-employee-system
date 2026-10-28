"""Allow the same position name at multiple grades; track one-time initial data."""
from alembic import op
import sqlalchemy as sa
from app.models import InitialDataState

revision='20261028_01'
down_revision='20261027_03'

def upgrade():
    bind=op.get_bind()
    uniques=sa.inspect(bind).get_unique_constraints('positions')
    old=next((u for u in uniques if set(u['column_names'])=={'department_id','name'}),None)
    if old:
        convention={'uq':'uq_%(table_name)s_%(column_0_name)s_%(column_1_name)s'}
        with op.batch_alter_table('positions',recreate='always',naming_convention=convention) as batch:
            batch.drop_constraint(old['name'] or 'uq_positions_department_id_name',type_='unique')
            batch.create_unique_constraint('uq_position_department_name_grade',['department_id','name','grade'])
    InitialDataState.__table__.create(bind,checkfirst=True)

def downgrade():
    raise RuntimeError('多职级职位不能无损合并，请使用备份恢复至独立数据库')
