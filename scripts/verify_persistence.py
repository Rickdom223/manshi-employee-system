"""Verify database, password and session persistence using a private restored copy."""
from pathlib import Path
from contextlib import closing
import json,os,socket,sqlite3,subprocess,sys,tempfile,time,urllib.request,http.cookiejar
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.core.config import database_path

def main():
 with tempfile.TemporaryDirectory(prefix='manshi-session-restore-') as directory:
  restored=Path(directory)/'restored.sqlite3'
  with closing(sqlite3.connect(database_path())) as source,closing(sqlite3.connect(restored)) as target:
   source.backup(target);assert target.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
   counts={table:target.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] for table in ['employees','departments','attendance_records','payroll_records','production_tasks']}
   # Change a password only in the disposable copy; test both hash and session survival.
   from app.core.security import password_hash
   password='Verify123'
   target.execute('UPDATE users SET password_hash=? WHERE username=?',(password_hash.hash(password),'ljm'));target.commit()
  opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
  results=[]
  for index in range(2):
   with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
   process=subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(port)],cwd=ROOT/'backend',env=dict(os.environ,DATABASE_PATH=str(restored),ALLOWED_ORIGINS='http://127.0.0.1:3000'),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   try:
    origin=f'http://127.0.0.1:{port}'
    for _ in range(100):
     try:
      with urllib.request.urlopen(origin+'/api/health',timeout=1):break
     except OSError:
      if process.poll() is not None:raise RuntimeError('验证进程启动失败')
      time.sleep(.1)
    if index==0:
     request=urllib.request.Request(origin+'/api/auth/login',data=json.dumps({'username':'ljm','password':password}).encode(),headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:3000'})
     with opener.open(request) as r:assert r.status==200
    with opener.open(origin+'/api/auth/me') as r:assert json.load(r)['data']['username']=='ljm'
    with opener.open(origin+'/api/employees?status=all') as r:assert json.load(r)['total']==counts['employees']
    with closing(sqlite3.connect(restored)) as db:
     assert all(db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]==count for table,count in counts.items())
     assert password_hash.verify(password,db.execute("SELECT password_hash FROM users WHERE username='ljm'").fetchone()[0])
    results.append({'restart':index+1,'status':'passed','session_restored':True,'password_preserved':True,'counts':counts})
   finally:process.terminate();process.wait(timeout=10)
  print(json.dumps({'backup_integrity':'ok','restored_process_checks':results}))

if __name__=='__main__':main()
