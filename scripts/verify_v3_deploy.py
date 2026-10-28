"""Exercise Vite same-origin proxy and persistence across a real backend restart."""
import os,sys,subprocess,socket,tempfile,time,json
from pathlib import Path
import httpx
from process_control import stop_process_tree,uvicorn_command

ROOT=Path(__file__).resolve().parents[1]
def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));return sock.getsockname()[1]

def ready(url,process):
    for _ in range(100):
        if process.poll() is not None:raise RuntimeError('服务意外退出')
        try:
            if httpx.get(url,timeout=1).status_code==200:return
        except httpx.HTTPError:pass
        time.sleep(.1)
    raise RuntimeError('服务启动超时')

def main():
    result={}
    with tempfile.TemporaryDirectory(prefix='manshi-deploy-') as directory:
        assert Path(directory).resolve().parent==Path(tempfile.gettempdir()).resolve()
        backend_port,web_port=free_port(),free_port();base=f'http://127.0.0.1:{web_port}'
        env=dict(os.environ,DATABASE_PATH=str(Path(directory)/'persistent.sqlite3'),SESSION_SECRET_KEY='deployment-test-secret-more-than-32-characters',API_PROXY_TARGET=f'http://127.0.0.1:{backend_port}',COOKIE_SECURE='false',APP_SERVE_STATIC='false',INITIAL_DATA_MODE='empty')
        for args in [['-m','alembic','upgrade','head'],['-m','app.scripts.init_data']]:subprocess.run([sys.executable,*args],cwd=ROOT/'backend',env=env,check=True,capture_output=True)
        def start_backend():return subprocess.Popen(uvicorn_command('app.main:app','--port',str(backend_port)),cwd=ROOT/'backend',env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        backend=start_backend()
        web=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',str(web_port)],cwd=ROOT/'frontend',env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            ready(base+'/api/health',web)
            with httpx.Client(base_url=base,headers={'Origin':base}) as client:
                def login(name,password):
                    response=client.post('/api/auth/login',json={'username':name,'password':password});assert response.status_code==200,response.text
                    client.headers['X-CSRF-Token']=response.json()['data']['csrf_token']
                    return response
                login('admin','Admin123')
                departments=client.get('/api/departments').json()['data'];d=departments[0]['id']
                response=client.post('/api/admin/bootstrap-first-hr',json={'employee_no':'HR001','name':'持久化人事','department_id':d,'position_name':'人事负责人','hire_date':'2026-01-01'})
                assert response.status_code==200,response.text
                hr=response.json()['data'];login('持久化人事','Aa123')
                response=client.post('/api/employees',json={'employee_no':'P001','name':'持久化员工','department_id':d,'position_id':hr['position_id'],'hire_date':'2026-01-01'})
                assert response.status_code==200,response.text
                employee=response.json()['data']
                assert client.post('/api/salaries',json={'employee_id':employee['id'],'year':2026,'month':10,'amount':'9876.54'}).status_code==200
                login('持久化员工','Aa123')
                punch=client.post('/api/me/punch-in');assert punch.status_code==200
                punch_date=punch.json()['data']['punch_date']
                assert client.post('/api/me/leaves',json={'leave_type':'事假','start_date':'2026-11-02','end_date':'2026-11-02','reason':'持久化验证'}).status_code==200
                stop_process_tree(backend);backend=start_backend();ready(base+'/api/health',web)
                assert client.get('/api/auth/me').status_code==200
                assert client.get('/api/me/salaries').json()['data'][0]['amount']=='9876.54'
                assert client.get('/api/me/leaves').json()['data'][0]['reason']=='持久化验证'
                assert next(d for d in client.get('/api/me/attendance',params={'month':punch_date[:7]}).json()['data']['daily'] if d['date']==punch_date)['punch_in']
                identity=client.get('/api/me/employee').json()['data'];assert identity['id']==employee['id'] and identity['account_username']=='持久化员工'
                result['backend_restart_persistence']='passed';result['cookie_csrf_via_vite_proxy']='passed'
                response=client.get('/my/salaries');assert response.status_code==200 and '<div id="app">' in response.text
                response=client.get('/api/nonexistent');assert response.status_code==404 and response.headers['content-type'].startswith('application/json')
                result['development_spa_refresh_api_boundary']='passed'
        finally:
            for process in [web,backend]:
                stop_process_tree(process)
    (ROOT/'docs/v3-deployment-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
