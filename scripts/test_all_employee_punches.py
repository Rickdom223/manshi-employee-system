"""Test every current employee on a read-only snapshot, leaving the live DB alone."""
import csv,hashlib,hmac,json,os,secrets,socket,sqlite3,subprocess,sys,tempfile,time
from contextlib import closing
from datetime import datetime,timedelta,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.core.config import database_path
from app.core.security import password_hash
from process_control import uvicorn_command,stop_process_tree

REPORT=ROOT/'docs/all-employee-punch-results.json'

def readonly(path):
    return sqlite3.connect(f'{Path(path).resolve().as_uri()}?mode=ro',uri=True)

def source_state(path,day):
    with closing(readonly(path)) as db:
        credentials=db.execute('SELECT id,username,password_hash FROM users ORDER BY id').fetchall()
        return {'credentials_digest':hashlib.sha256(json.dumps(credentials).encode()).hexdigest(),
                'punch_rows':db.execute('SELECT id,employee_id,punch_date,punch_type,punch_time FROM punch_records ORDER BY id').fetchall(),
                'today_count':db.execute('SELECT count(*) FROM punch_records WHERE punch_date=?',(day,)).fetchone()[0]}

def ready(base,server):
    for _ in range(100):
        if server.poll() is not None:raise RuntimeError('隔离测试服务启动失败，请查看测试日志')
        try:
            if httpx.get(base+'/api/health',timeout=1,trust_env=False).status_code==200:return
        except httpx.HTTPError:pass
        time.sleep(.1)
    raise RuntimeError('隔离测试服务启动超时')

def markdown(report):
    rows=['# 全员上下班打卡测试', '',f'测试日期：{report["business_date"]}。本次使用当前数据库的隔离副本，未向实际系统写入测试打卡。', '',
          f'共{report["employee_count"]}名员工；{report["eligible_count"]}名启用的在职员工逐一完成网页上班/下班打卡；{report["blocked_count"]}名离职或停用员工应被拒绝。', '',
          '仅在副本中使用临时测试密码，以覆盖已经修改密码的账号；实际员工账号和密码保持不变。副本测试当天先清空复制来的打卡记录，再通过网页按钮真实调用API。', '',
          '| 工号 | 姓名 | 角色 | 账号状态 | 上班打卡 | 下班打卡 | 重复/顺序/隔离或停用拦截 | 重启验证 | 结果 |',
          '|---|---|---|---|---|---|---|---|---|']
    labels={'HR':'HR','SUPERVISOR':'部门主管','EMPLOYEE':'普通员工'}
    def safe(value):return str(value).replace('|','／').replace('\n',' ')
    for row in report['employees']:
        denied=row['expected_access']=='denied'
        rows.append('| '+' | '.join(map(safe,[row['employee_no'],row['name'],labels.get(row['role'],row['role']), '离职/停用' if denied else '在职启用',
            '拒绝（401）' if denied and row.get('blocked_punch_in')==401 else ('通过' if row.get('punch_in')==200 else '未通过'),
            '拒绝（401）' if denied and row.get('blocked_punch_out')==401 else ('通过' if row.get('punch_out')==200 else '未通过'),
            '通过' if row.get('boundary_checks') else row.get('reason','未通过'), '通过' if row.get('restart_verified') else '—', '通过' if row['status']=='passed' else '失败']))+' |')
    rows+=['',f'隔离副本测试日打卡数量：{report["test_punch_count"]}条（每位获准员工恰好1条上班、1条下班）。',
           f'实际系统测试前/后打卡总数：{report["source_punch_count_before"]} / {report["source_punch_count_after"]}；原打卡逐条不变：{report["source_punch_records_unchanged"]}；原账号密码不变：{report["source_credentials_unchanged"]}。',
           f'独立系统管理员打卡拦截：{report["admin_check"]["status"]}。', '',
           '检查项目：每人实际网页登录与按钮调用、服务器时间、先下班拦截、重复上/下班409、本人记录与身份隔离、离职/停用账号登录及持旧会话打卡401、后端重启后的会话与原始打卡持久化。', '',
           '当前实际考勤规则尚未配置，原始打卡允许保存；日统计应显示“尚未配置规则”，不伪造迟到/早退判定。' if report['attendance_rule_count']==0 else f'本次保留实际库已有的{report["attendance_rule_count"]}条考勤规则。', '',
           '运行：在项目根目录执行 `backend/.venv/Scripts/python.exe scripts/test_all_employee_punches.py`。测试只修改临时副本，结束后删除副本和临时会话。']
    return '\n'.join(rows)+'\n'

def main():
    zone=ZoneInfo(os.getenv('BUSINESS_TIMEZONE','Asia/Shanghai'));now=datetime.now(zone);day=now.date().isoformat()
    source=database_path().resolve();before=source_state(source,day)
    runtime=ROOT/'deploy/runtime';runtime.mkdir(parents=True,exist_ok=True)
    server=None;browser_result=None;report=None
    with tempfile.TemporaryDirectory(prefix='.runtime-punch-',dir=ROOT) as directory:
        directory=Path(directory).resolve();assert directory.parent==ROOT.resolve()
        clone=directory/'test.sqlite3';assert clone!=source
        with closing(readonly(source)) as actual,closing(sqlite3.connect(clone)) as copied:actual.backup(copied)
        subprocess.run([sys.executable,'-m','alembic','upgrade','head'],cwd=ROOT/'backend',env=dict(os.environ,DATABASE_PATH=str(clone)),capture_output=True,check=True)
        with closing(sqlite3.connect(clone)) as db:
            employees=[dict(zip(['id','employee_no','name','employment_status','user_id','username','role','is_active'],row)) for row in db.execute('SELECT e.id,e.employee_no,e.full_name,e.status,u.id,u.username,u.role,u.is_active FROM employees e LEFT JOIN users u ON u.employee_id=e.id ORDER BY e.id')]
            if any(e['user_id'] is None for e in employees):raise RuntimeError('发现未关联账号的员工，需要先修复开户数据')
            system_accounts=[dict(zip(['user_id','username','role','is_active'],row)) for row in db.execute('SELECT id,username,role,is_active FROM users WHERE employee_id IS NULL')]
            rule_count=db.execute('SELECT count(*) FROM attendance_rules').fetchone()[0]
            test_password='Test1-'+secrets.token_urlsafe(24)
            # Changes are strictly to this disposable copy, never to the source.
            db.execute('DELETE FROM sessions')
            db.execute('DELETE FROM punch_records WHERE punch_date=?',(day,))
            db.execute('UPDATE users SET password_hash=?',(password_hash.hash(test_password),))
            server_secret=secrets.token_urlsafe(48)
            for employee in employees:
                employee['expected_access']='allowed' if employee['employment_status']=='active' and employee['is_active'] else 'denied'
                if employee['expected_access']=='denied':
                    token=secrets.token_urlsafe(48);csrf=hmac.new(server_secret.encode(),token.encode(),hashlib.sha256).hexdigest()
                    db.execute('INSERT INTO sessions(token_hash,user_id,csrf_token_hash,expires_at) VALUES(?,?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),employee['user_id'],hashlib.sha256(csrf.encode()).hexdigest(),(datetime.now(timezone.utc)+timedelta(hours=8)).replace(tzinfo=None).isoformat()))
                    employee['stale_cookie']=token;employee['stale_csrf']=csrf
            db.commit()
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        base=f'http://127.0.0.1:{port}'
        manifest=directory/'manifest.json';browser_file=directory/'browser-results.json';sessions_file=directory/'test-sessions.json'
        offset=now.strftime('%z');offset=offset[:3]+':'+offset[3:]
        manifest.write_text(json.dumps(dict(employees=employees,system_accounts=system_accounts,test_password=test_password,business_date=day,utc_offset=offset),ensure_ascii=False),encoding='utf-8')
        env=dict(os.environ,DATABASE_PATH=str(clone),SESSION_SECRET_KEY=server_secret,APP_SERVE_STATIC='true',COOKIE_SECURE='false',E2E_BASE_URL=base,PUNCH_MANIFEST=str(manifest),PUNCH_RESULTS=str(browser_file),PUNCH_SESSIONS=str(sessions_file))
        log=(runtime/'all-employee-punch-test.log').open('w',encoding='utf-8')
        def start():return subprocess.Popen(uvicorn_command('app.main:app','--host','127.0.0.1','--port',str(port)),cwd=ROOT/'backend',env=env,stdout=log,stderr=log)
        try:
            server=start();ready(base,server)
            result=subprocess.run(['node','tests/all-employee-punches.mjs'],cwd=ROOT/'frontend',env=env)
            if not browser_file.exists():raise RuntimeError('浏览器没有生成测试结果')
            browser_result=json.loads(browser_file.read_text(encoding='utf-8'))
            stop_process_tree(server);server=start();ready(base,server)
            sessions=json.loads(sessions_file.read_text(encoding='utf-8'))
            for row in browser_result['employees']:
                if row['expected_access']!='allowed' or row['status']!='passed':continue
                try:
                    with httpx.Client(base_url=base,cookies={'manshi_session':sessions[str(row['id'])]},timeout=10,trust_env=False) as client:
                        me=client.get('/api/auth/me');assert me.status_code==200 and me.json()['data']['employee_id']==row['id']
                        response=client.get('/api/me/attendance',params={'month':day[:7]});assert response.status_code==200
                        daily=next(d for d in response.json()['data']['daily'] if d['date']==day)
                        assert daily['punch_in']==row['punch_in_time'] and daily['punch_out']==row['punch_out_time']
                    row['restart_verified']=True
                except Exception as exc:row.update(status='failed',reason='重启持久化验证失败：'+str(exc))
            with closing(sqlite3.connect(clone)) as db:
                counts={e:(ins,outs) for e,ins,outs in db.execute("SELECT employee_id,sum(punch_type='IN'),sum(punch_type='OUT') FROM punch_records WHERE punch_date=? GROUP BY employee_id",(day,))}
                for row in browser_result['employees']:
                    expected=(1,1) if row['expected_access']=='allowed' else (0,0)
                    row['database_verified']=counts.get(row['id'],(0,0))==expected
                    if not row['database_verified']:row.update(status='failed',reason='原始打卡数量或身份不符合预期')
                test_count=db.execute('SELECT count(*) FROM punch_records WHERE punch_date=?',(day,)).fetchone()[0]
            after=source_state(source,day)
            report=dict(business_date=day,source_database_opened_readonly=True,test_database_isolated=True,test_only_passwords=True,employee_count=len(employees),eligible_count=sum(e['expected_access']=='allowed' for e in employees),blocked_count=sum(e['expected_access']=='denied' for e in employees),attendance_rule_count=rule_count,test_punch_count=test_count,source_punch_count_before=len(before['punch_rows']),source_punch_count_after=len(after['punch_rows']),source_punch_records_unchanged=before['punch_rows']==after['punch_rows'],source_credentials_unchanged=before['credentials_digest']==after['credentials_digest'],employees=browser_result['employees'],admin_check=browser_result['admin_check'],page_errors=browser_result['page_errors'])
            report['status']='passed' if all(r['status']=='passed' for r in report['employees']) and report['admin_check']['status']=='passed' and not report['page_errors'] and report['source_punch_records_unchanged'] and report['source_credentials_unchanged'] else 'failed'
            REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            (ROOT/'docs/all-employee-punch-results.md').write_text(markdown(report),encoding='utf-8')
            with (ROOT/'docs/all-employee-punch-results.csv').open('w',encoding='utf-8-sig',newline='') as file:
                writer=csv.writer(file);writer.writerow(['工号','姓名','角色','准入','上班结果','下班结果','边界验证','重启验证','原始记录验证','结果','说明'])
                for row in report['employees']:writer.writerow([row['employee_no'],row['name'],row['role'],row['expected_access'],row.get('punch_in',row.get('blocked_punch_in')),row.get('punch_out',row.get('blocked_punch_out')),row.get('boundary_checks',False),row.get('restart_verified',False),row['database_verified'],row['status'],row.get('reason','')])
            print(json.dumps({key:report[key] for key in ['status','employee_count','eligible_count','blocked_count','test_punch_count','source_punch_records_unchanged','source_credentials_unchanged']},ensure_ascii=False))
            return 0 if report['status']=='passed' else 1
        finally:
            if server:stop_process_tree(server)
            log.close()

if __name__=='__main__':raise SystemExit(main())
