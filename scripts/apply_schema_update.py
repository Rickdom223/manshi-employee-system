"""Back up and migrate without changing any existing non-gender business values."""
import sys,sqlite3,subprocess,json,uuid
from pathlib import Path
from contextlib import closing
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.core.config import database_path

def snapshot(connection):
    result={}
    for (table,) in connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name!='alembic_version' ORDER BY name"):
        columns=[r[1] for r in connection.execute(f'PRAGMA table_info("{table}")') if not(table=='employees' and r[1]=='gender')]
        selected=','.join('"'+name+'"' for name in columns)
        result[table]=(columns,connection.execute(f'SELECT {selected} FROM "{table}" ORDER BY 1').fetchall())
    return result

def main():
    target=database_path().resolve()
    if not target.is_relative_to(ROOT.resolve()):raise RuntimeError('迁移目标必须位于本项目目录')
    stamp=datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6]
    backup=ROOT/'backend/backups'/f'before-remove-gender-{stamp}.sqlite3'
    backup.parent.mkdir(parents=True,exist_ok=True)
    if backup.exists():raise RuntimeError('备份已存在，拒绝覆盖')
    with closing(sqlite3.connect(f'{target.as_uri()}?mode=ro',uri=True)) as old,closing(sqlite3.connect(backup)) as saved:
        before=snapshot(old);old.backup(saved)
        assert saved.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    subprocess.run([sys.executable,'-m','alembic','upgrade','head'],cwd=ROOT/'backend',check=True)
    with closing(sqlite3.connect(target)) as db:
        assert 'gender' not in {row[1] for row in db.execute('PRAGMA table_info(employees)')}
        assert snapshot(db)==before,'除性别外的数据发生变化，请使用迁移前备份检查'
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert not db.execute('PRAGMA foreign_key_check').fetchall()
        result=dict(status='passed',removed_attribute='gender',other_data_unchanged=True,employees=db.execute('SELECT count(*) FROM employees').fetchone()[0],accounts=db.execute('SELECT count(*) FROM users').fetchone()[0],backup=str(backup))
    (ROOT/'docs/remove-gender-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
