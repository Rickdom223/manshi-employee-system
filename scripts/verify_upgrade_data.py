"""Compare original columns against the pre-upgrade private backup without printing records."""
from pathlib import Path
from contextlib import closing
import sqlite3,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.core.config import database_path
backup=ROOT/'backend/backups/pre-spec-20261027.sqlite3'
if not backup.exists():raise SystemExit('本机迁移前备份不存在；此检查仅用于本次增量升级现场证据')
results=[]
with closing(sqlite3.connect(backup)) as before,closing(sqlite3.connect(database_path())) as after:
 for table in ['users','departments','positions','employees','skills','employee_skills']:
  columns=[r[1] for r in before.execute(f'PRAGMA table_info({table})') if r[1]!='role']
  old=before.execute(f'SELECT {",".join(columns)} FROM {table}').fetchall()
  new=dict((r[0],r) for r in after.execute(f'SELECT {",".join(columns)} FROM {table}'))
  assert all(new.get(r[0])==r for r in old),table+'原记录发生变化'
  results.append({'table':table,'original_records':len(old),'preserved':True})
 assert after.execute('PRAGMA foreign_key_check').fetchall()==[]
print(json.dumps({'legacy_data':results,'foreign_keys':'ok'}))
