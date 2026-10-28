"""Explicit rebuild: validate -> empty staged DB -> seed -> backup -> atomic swap."""
import argparse,json,os,sqlite3,subprocess,sys,uuid
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from contextlib import closing

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.core.config import database_path
from app.core.database import make_engine
from app.scripts.initialize_v3 import initialize
from app.services.initial_roster import DEFAULT_ROSTER,read_roster,install_roster,roster_summary
from sqlalchemy.orm import Session

def rebuild(target,source=DEFAULT_ROSTER,report_path=None):
    target=Path(target).resolve();source=Path(source).resolve()
    if not target.is_relative_to(ROOT.resolve()):raise ValueError('重建目标必须位于本项目目录内')
    read_roster(source)  # Any invalid source fails before touching the live DB.
    target.parent.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6]
    candidate=target.with_name(f'{target.stem}-rebuild-{stamp}.sqlite3')
    if candidate.exists():raise RuntimeError('候选文件已存在，拒绝覆盖')
    env=dict(os.environ,DATABASE_PATH=str(candidate),INITIAL_DATA_MODE='empty')
    subprocess.run([sys.executable,'-m','alembic','upgrade','head'],cwd=ROOT/'backend',env=env,check=True,capture_output=True)
    with closing(sqlite3.connect(candidate)) as raw:
        tables=[r[0] for r in raw.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT IN ('alembic_version','sqlite_sequence')")]
        assert all(raw.execute('SELECT count(*) FROM "'+table+'"').fetchone()[0]==0 for table in tables)
    engine=make_engine(candidate)
    try:
        with Session(engine) as db:
            initialize(db);result=install_roster(db,source)
            from app.models import User,Salary,PunchRecord,LeaveRequest,Attendance,Payroll,ProductionTask,LoginSession
            from sqlalchemy import select,func
            assert [(u.username,u.employee_id) for u in db.scalars(select(User).where(User.role=='SYS_ADMIN'))]==[('admin',None)]
            empty_counts={m.__tablename__:db.scalar(select(func.count()).select_from(m)) for m in [Salary,PunchRecord,LeaveRequest,Attendance,Payroll,ProductionTask,LoginSession]}
            assert not any(empty_counts.values())
    finally:engine.dispose()
    with closing(sqlite3.connect(candidate)) as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert db.execute('PRAGMA foreign_key_check').fetchall()==[]
    backup=None
    if target.exists():
        if any(target.with_name(target.name+suffix).exists() for suffix in ['-wal','-shm']):raise RuntimeError('旧库仍有WAL/共享文件，请先停止后端并完成检查点再重建')
        backup=(ROOT/'backend/backups'/f'before-approved-roster-{stamp}.sqlite3').resolve()
        backup.parent.mkdir(parents=True,exist_ok=True)
        if backup.exists():raise RuntimeError('备份文件已存在，拒绝覆盖')
        with closing(sqlite3.connect(f'{target.as_uri()}?mode=ro',uri=True)) as old,closing(sqlite3.connect(backup)) as saved:
            old.backup(saved)
            saved.commit()
            assert saved.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    # Both are explicitly verified project paths; swap one file, never merge rows.
    assert candidate.parent==target.parent and candidate.is_relative_to(ROOT.resolve())
    os.replace(candidate,target)
    result.update(database=str(target),backup=str(backup) if backup else None,started_from_empty=True,old_rows_copied=0,empty_business_tables=empty_counts)
    if report_path:Path(report_path).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return result

def main():
    parser=argparse.ArgumentParser(description='按已确认员工数据重建数据库：先备份旧库，不合并旧数据')
    parser.add_argument('--source',type=Path,default=DEFAULT_ROSTER)
    parser.add_argument('--database',type=Path,default=None)
    args=parser.parse_args()
    print(json.dumps(rebuild(args.database or database_path(),args.source,ROOT/'docs/initial-data-reset-results.json'),ensure_ascii=False))

if __name__=='__main__':main()
