"""Smoke-test the explicitly marked static-hosting fallback, including API 404 isolation."""
from pathlib import Path
import os,socket,subprocess,sys,time,urllib.request,urllib.error,json
ROOT=Path(__file__).resolve().parents[1]
with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
process=subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(port)],cwd=ROOT/'backend',env=dict(os.environ,APP_SERVE_STATIC='true'),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:
 base=f'http://127.0.0.1:{port}'
 for _ in range(100):
  try:
   with urllib.request.urlopen(base+'/api/health',timeout=1):break
  except OSError:
   if process.poll() is not None:raise RuntimeError('静态服务启动失败')
   time.sleep(.1)
 results=[]
 for path in ['/admin/dashboard','/employee/profile']:
  with urllib.request.urlopen(base+path) as response:
   assert response.status==200 and '<div id="app">' in response.read().decode()
   results.append({'path':path,'status':200,'spa':True})
 try:urllib.request.urlopen(base+'/api/does-not-exist')
 except urllib.error.HTTPError as error:
  assert error.code==404 and 'error' in json.load(error)
  results.append({'path':'/api/does-not-exist','status':404,'json':True})
 else:raise AssertionError('API404不应回退为HTML')
 print(json.dumps({'results':results}))
finally:process.terminate();process.wait(timeout=10)
