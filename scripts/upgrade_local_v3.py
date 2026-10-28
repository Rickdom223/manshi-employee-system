"""Back up and upgrade the configured SQLite DB, verifying preserved identities."""
import sys,sqlite3,subprocess,json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.core.config import database_path

def main():
    path=database_path();backup=None;before={}
    if path.exists():
        backup=ROOT/'backend/backups'/('pre-v3-'+datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y%m%d-%H%M%S')+'.sqlite3')
        backup.parent.mkdir(parents=True,exist_ok=True)
        if backup.exists():raise RuntimeError('备份文件已存在，请稍后重试')
        with sqlite3.connect(path) as source,sqlite3.connect(backup) as target:
            source.backup(target)
            names={r[0] for r in source.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if 'employees' in names:before['employee_ids']=[r[0] for r in source.execute('SELECT id FROM employees ORDER BY id')]
            if 'users' in names:before['credentials']=source.execute('SELECT id,username,password_hash FROM users ORDER BY id').fetchall()
            before['legacy_counts']={t:source.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ['payroll_records','attendance_records','leave_requests'] if t in names}
    for args in [['-m','alembic','upgrade','head'],['-m','app.scripts.init_data']]:
        subprocess.run([sys.executable,*args],cwd=ROOT/'backend',check=True)
    with sqlite3.connect(path) as db:
        current_ids={r[0] for r in db.execute('SELECT id FROM employees')}
        assert set(before.get('employee_ids',[]))<=current_ids
        assert all(db.execute('SELECT username,password_hash FROM users WHERE id=?',(id,)).fetchone()==(username,hash_) for id,username,hash_ in before.get('credentials',[]))
        assert all(db.execute('SELECT count(*) FROM '+table).fetchone()[0]==count for table,count in before.get('legacy_counts',{}).items())
        assert db.execute('SELECT count(*) FROM departments').fetchone()[0]==4
        assert db.execute('SELECT count(*) FROM employees e WHERE NOT EXISTS(SELECT 1 FROM users u WHERE u.employee_id=e.id)').fetchone()[0]==0
        assert db.execute('PRAGMA foreign_key_check').fetchall()==[]
        result=dict(status='passed',backup=str(backup) if backup else None,employees_preserved=len(before.get('employee_ids',[])),existing_credentials_preserved=len(before.get('credentials',[])),legacy_business_counts_preserved=before.get('legacy_counts',{}),departments=4,accounts=db.execute('SELECT count(*) FROM users').fetchone()[0],employee_count=len(current_ids))
    (ROOT/'docs/v3-local-upgrade.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
