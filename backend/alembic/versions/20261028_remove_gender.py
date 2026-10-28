"""Remove the unused employee gender attribute, preserving all remaining columns."""
from alembic import op
import sqlalchemy as sa

revision='20261028_02'
down_revision='20261028_01'

def upgrade():
    bind=op.get_bind()
    if 'gender' in {column['name'] for column in sa.inspect(bind).get_columns('employees')}:
        with op.batch_alter_table('employees',recreate='always') as batch:
            batch.drop_column('gender')

def downgrade():
    # Values intentionally removed by the user cannot be reconstructed.
    op.add_column('employees',sa.Column('gender',sa.String(),nullable=True))
