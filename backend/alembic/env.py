from alembic import context
from sqlalchemy import engine_from_config
from app.core.database import engine, Base
from app import models

with engine.connect() as connection:
    connection.exec_driver_sql('PRAGMA foreign_keys=OFF')
    connection.commit()
    context.configure(connection=connection, target_metadata=Base.metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()
    connection.exec_driver_sql('PRAGMA foreign_keys=ON')
    assert not connection.exec_driver_sql('PRAGMA foreign_key_check').fetchall()
