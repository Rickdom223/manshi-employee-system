"""User-authorized short shift in the CURRENT demo DB, using real server times."""
import argparse,json,os,sqlite3,subprocess,sys,tempfile,time,uuid
from contextlib import closing
from datetime import datetime,timedelta,timezone
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import urlparse
import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.core.config import database_path
from app.core.database import SessionLocal
from app.core.security import create_session,COOKIE,digest
from app.models import User,Employee,LoginSession,PunchRecord,AttendanceRule,AuditLog,LeaveRequest
from app.services.v3_attendance import business_now
from fastapi import Response
from sqlalchemy import select

CASES=[('normal','韩涛','正常'),('late','吴琪','迟到'),('early','孙颖','早退'),('missing','林墨','缺下班卡'),('absent','赵欣','缺勤')]

def finish_current(base):
    """Preserve completed examples and approved leave; fill only the new late pair."""
    if urlparse(base).hostname not in {'127.0.0.1','localhost'}:raise ValueError('仅允许本机演示系统')
    day=business_now().date();sessions=[];clients={};rows=[];tokens={}
    backups=sorted((ROOT/'backend/backups').glob(f'before-short-attendance-{day}-*.sqlite3'),key=lambda p:p.stat().st_mtime)
    if not backups:raise RuntimeError('缺少本次演示前备份')
    backup=backups[-1]
    with SessionLocal() as db:
        rule=db.scalar(select(AttendanceRule).where(AttendanceRule.effective_date==day))
        if not rule:raise RuntimeError('今天没有已配置的短班次')
        begin=datetime.fromisoformat(f'{day}T{rule.start_time}');end=datetime.fromisoformat(f'{day}T{rule.end_time}')
        if (end-begin).total_seconds()!=120 or business_now().replace(tzinfo=None)<=end:raise RuntimeError('仅用于已结束的2分钟班次')
        before=[(u.id,u.username,u.password_hash,u.role,u.is_active) for u in db.scalars(select(User).order_by(User.id))]
        def signed(key,user):
            response=Response();csrf=create_session(db,user,response);cookie=SimpleCookie();cookie.load(response.headers['set-cookie']);token=cookie[COOKIE].value
            session=db.scalar(select(LoginSession).where(LoginSession.token_hash==digest(token)));sessions.append(session.id);tokens[key]=token
            client=httpx.Client(base_url=base,cookies={COOKIE:token},headers={'Origin':base,'X-CSRF-Token':csrf},timeout=10,trust_env=False);clients[key]=client
            return client
        try:
            all_cases=CASES+[('leave','周可','已批准请假')]
            for key,name,expected in all_cases:
                employee=db.scalar(select(Employee).where(Employee.full_name==name));user=db.scalar(select(User).where(User.employee_id==employee.id))
                if employee.status!='active' or not user.is_active:raise RuntimeError(f'{name}账号不可用')
                approved=db.scalar(select(LeaveRequest.id).where(LeaveRequest.employee_id==employee.id,LeaveRequest.status=='approved',LeaveRequest.start_date<=day,LeaveRequest.end_date>=day))
                if key!='leave' and approved:raise RuntimeError(f'{name}有获批请假，不能用作{expected}场景')
                client=signed(key,user)
                if key=='late':
                    for kind,path in [('IN','in'),('OUT','out')]:
                        existing=db.scalar(select(PunchRecord.id).where(PunchRecord.employee_id==employee.id,PunchRecord.punch_date==day,PunchRecord.punch_type==kind))
                        if not existing:
                            response=client.post('/api/me/punch-'+path);assert response.status_code==200,response.text
                            print(f'{name} {path}: {response.json()["data"]["punch_time"]}',flush=True)
                response=client.get('/api/me/attendance',params={'month':day.strftime('%Y-%m')});assert response.status_code==200
                data=response.json()['data'];daily=next(r for r in data['daily'] if r['date']==day.isoformat())
                assert daily['status']==expected,(name,daily)
                rows.append(dict(employee_no=employee.employee_no,name=name,scenario=key,status=daily['status'],punch_in=daily['punch_in'],punch_out=daily['punch_out'],**{k:data[k] for k in ['late_count','early_count','missing_punch_count','absent_days']}))
            with tempfile.TemporaryDirectory(prefix='.runtime-short-attendance-',dir=ROOT) as directory:
                assert Path(directory).resolve().parent==ROOT.resolve()
                proof=Path(directory)/'proof.json';proof.write_text(json.dumps(dict(base=base,date=day.isoformat(),rows=[dict(r,cookie=tokens[r['scenario']]) for r in rows]),ensure_ascii=False),encoding='utf-8')
                result=subprocess.run(['node','tests/short-attendance-proof.mjs'],cwd=ROOT/'frontend',env=dict(os.environ,SHORT_ATTENDANCE_PROOF=str(proof)))
                assert result.returncode==0,'网页验证失败'
            db.expire_all();assert [(u.id,u.username,u.password_hash,u.role,u.is_active) for u in db.scalars(select(User).order_by(User.id))]==before
            with closing(sqlite3.connect(backup)) as old:
                originals=old.execute('SELECT id,employee_id,punch_date,punch_type,punch_time FROM punch_records').fetchall()
            with closing(sqlite3.connect(database_path())) as current:
                assert all(current.execute('SELECT id,employee_id,punch_date,punch_type,punch_time FROM punch_records WHERE id=?',(row[0],)).fetchone()==row for row in originals)
                created=current.execute('SELECT count(*) FROM punch_records').fetchone()[0]-len(originals)
            actor=db.scalar(select(User).where(User.role=='SYS_ADMIN',User.is_active==True))
            db.add(AuditLog(actor_user_id=actor.id,action='SHORT_ATTENDANCE_DEMO',target_type='attendance_rules',target_id=rule.id,summary='用户要求当前页面展示正常、迟到、早退、缺卡、缺勤；周可获批请假保留并豁免，吴琪展示迟到'))
            db.commit()
            report=dict(status='passed',date=day.isoformat(),rule_id=rule.id,rule=dict(effective_date=day.isoformat(),start_time=rule.start_time,end_time=rule.end_time,late_grace_minutes=rule.late_grace_minutes,early_grace_minutes=rule.early_grace_minutes),rows=rows,backup=str(backup),existing_records_preserved=len(originals),credentials_unchanged=True,new_punch_records=created)
            (ROOT/'docs/short-attendance-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            print(json.dumps(report,ensure_ascii=False),flush=True)
        finally:
            for client in clients.values():client.close()
            db.rollback()
            for id in sessions:
                session=db.get(LoginSession,id)
                if session:session.revoked_at=datetime.now(timezone.utc)
            db.commit()
    return 0

def wait_until(moment):
    while business_now()<moment:time.sleep(min(.5,max(.01,(moment-business_now()).total_seconds())))

def main():
    parser=argparse.ArgumentParser(description='按用户要求在当前系统运行约2分钟班次并留下5种打卡效果')
    parser.add_argument('--apply-to-current-demo',action='store_true',required=True)
    parser.add_argument('--finish-current-run',action='store_true')
    parser.add_argument('--base',default='http://127.0.0.1:3000')
    args=parser.parse_args()
    if urlparse(args.base).hostname not in {'127.0.0.1','localhost'}:raise ValueError('仅允许本机演示系统')
    if args.finish_current_run:return finish_current(args.base)
    target=database_path().resolve();run_id=uuid.uuid4().hex[:12];day=business_now().date()
    if not target.is_relative_to(ROOT.resolve()):raise ValueError('数据库必须位于项目目录内')
    backup=ROOT/'backend/backups'/f'before-short-attendance-{day}-{run_id}.sqlite3'
    backup.parent.mkdir(parents=True,exist_ok=True)
    with closing(sqlite3.connect(f'{target.as_uri()}?mode=ro',uri=True)) as source,closing(sqlite3.connect(backup)) as saved:
        source.backup(saved);assert saved.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    clients={};sessions=[];tokens={};report={};rows=[]
    with SessionLocal() as db:
        credentials=[(u.id,u.username,u.password_hash,u.role,u.is_active) for u in db.scalars(select(User).order_by(User.id))]
        original={p.id:(p.employee_id,p.punch_date,p.punch_type,p.punch_time) for p in db.scalars(select(PunchRecord))}
        if db.scalar(select(AttendanceRule.id).where(AttendanceRule.effective_date==day)):raise RuntimeError('今天已有考勤规则，拒绝覆盖历史规则')
        people={}
        for key,name,expected in CASES:
            employee=db.scalar(select(Employee).where(Employee.full_name==name))
            user=db.scalar(select(User).where(User.employee_id==employee.id)) if employee else None
            if not employee or employee.status!='active' or not user or not user.is_active:raise RuntimeError(f'{name}不是启用的在职员工')
            if db.scalar(select(LeaveRequest.id).where(LeaveRequest.employee_id==employee.id,LeaveRequest.status=='approved',LeaveRequest.start_date<=day,LeaveRequest.end_date>=day)):raise RuntimeError(f'{name}今天有获批请假，不能用于迟到/早退等场景')
            if db.scalar(select(PunchRecord.id).where(PunchRecord.employee_id==employee.id,PunchRecord.punch_date==day)):raise RuntimeError(f'{name}今天已有打卡，不能覆盖；请更换演示人选')
            people[key]=(employee,user,expected)
        hr=db.scalar(select(User).join(Employee,Employee.id==User.employee_id).where(User.role=='HR',User.is_active==True,Employee.status=='active'))
        actor=db.scalar(select(User).where(User.role=='SYS_ADMIN',User.is_active==True))
        if not hr or not actor:raise RuntimeError('缺少可用HR或系统管理员')
        def client_for(key,user):
            response=Response();csrf=create_session(db,user,response)
            cookie=SimpleCookie();cookie.load(response.headers['set-cookie']);token=cookie[COOKIE].value
            login=db.scalar(select(LoginSession).where(LoginSession.token_hash==digest(token)));sessions.append(login.id);tokens[key]=token
            client=httpx.Client(base_url=args.base,cookies={COOKIE:token},headers={'Origin':args.base,'X-CSRF-Token':csrf},timeout=10,trust_env=False)
            identity=client.get('/api/auth/me');assert identity.status_code==200 and identity.json()['data']['id']==user.id
            clients[key]=client;return client
        def punch(key,kind):
            response=clients[key].post('/api/me/punch-'+kind)
            assert response.status_code==200,response.text
            data=response.json()['data'];assert data['punch_date']==day.isoformat()
            print(f'{people[key][0].full_name} {kind}: {data["punch_time"]}',flush=True)
        try:
            hr_client=client_for('hr',hr)
            for key,(_,user,_) in people.items():client_for(key,user)
            start=(business_now()+timedelta(seconds=30)).replace(microsecond=0);end=start+timedelta(minutes=2)
            if end.date()!=day:raise RuntimeError('短班次不能跨日，请在当天稍早时间运行')
            rule=dict(effective_date=day.isoformat(),weekdays=sorted(set([0,1,2,3,4,day.weekday()])),start_time=start.strftime('%H:%M:%S'),end_time=end.strftime('%H:%M:%S'),late_grace_minutes=0,early_grace_minutes=0)
            response=hr_client.post('/api/attendance/rules',json=rule);assert response.status_code==200,response.text
            rule_id=response.json()['data']['id']
            print(f'今日短班次 {rule["start_time"]} — {rule["end_time"]}，迟到/早退容忍0分钟',flush=True)
            for key in ['normal','early','missing']:punch(key,'in')
            print('等待上班时刻后完成迟到打卡；林墨保留下班缺卡，赵欣保持未打卡。',flush=True)
            wait_until(start+timedelta(seconds=3));punch('late','in')
            wait_until(start+timedelta(minutes=1));punch('early','out')
            print('等待两分钟短班次结束，为正常和迟到员工完成下班打卡。',flush=True)
            wait_until(end+timedelta(seconds=2));punch('normal','out');punch('late','out')
            proof=[]
            for key,(employee,user,expected) in people.items():
                response=clients[key].get('/api/me/attendance',params={'month':day.strftime('%Y-%m')});assert response.status_code==200
                data=response.json()['data'];today=next(r for r in data['daily'] if r['date']==day.isoformat())
                assert today['status']==expected,(employee.full_name,today)
                assert data['today']['shift']['start_time']==rule['start_time']
                expected_counts={'normal':(0,0,0,0),'late':(1,0,0,0),'early':(0,1,0,0),'missing':(0,0,1,0),'absent':(0,0,0,1)}[key]
                assert tuple(data[k] for k in ['late_count','early_count','missing_punch_count','absent_days'])==expected_counts
                row=dict(employee_no=employee.employee_no,name=employee.full_name,scenario=key,status=today['status'],punch_in=today['punch_in'],punch_out=today['punch_out'],**{k:data[k] for k in ['late_count','early_count','missing_punch_count','absent_days']})
                rows.append(row);proof.append(dict(row,cookie=tokens[key]))
            with tempfile.TemporaryDirectory(prefix='.runtime-short-attendance-',dir=ROOT) as directory:
                assert Path(directory).resolve().parent==ROOT.resolve()
                file=Path(directory)/'proof.json';file.write_text(json.dumps(dict(base=args.base,date=day.isoformat(),rows=proof),ensure_ascii=False),encoding='utf-8')
                result=subprocess.run(['node','tests/short-attendance-proof.mjs'],cwd=ROOT/'frontend',env=dict(os.environ,SHORT_ATTENDANCE_PROOF=str(file)))
                assert result.returncode==0,'当前网页效果验证失败'
            db.expire_all()
            assert [(u.id,u.username,u.password_hash,u.role,u.is_active) for u in db.scalars(select(User).order_by(User.id))]==credentials
            assert all((db.get(PunchRecord,id).employee_id,db.get(PunchRecord,id).punch_date,db.get(PunchRecord,id).punch_type,db.get(PunchRecord,id).punch_time)==value for id,value in original.items())
            db.add(AuditLog(actor_user_id=actor.id,action='SHORT_ATTENDANCE_DEMO',target_type='attendance_rules',target_id=rule_id,summary=f'用户明确要求当前系统演示正常/迟到/早退/缺卡/缺勤；短班次{rule["start_time"]}-{rule["end_time"]}；批次{run_id}'))
            db.commit()
            report=dict(status='passed',date=day.isoformat(),rule_id=rule_id,rule=rule,rows=rows,backup=str(backup),existing_records_preserved=len(original),credentials_unchanged=True,new_punch_records=7)
            (ROOT/'docs/short-attendance-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            print(json.dumps(report,ensure_ascii=False),flush=True)
        finally:
            for client in clients.values():client.close()
            db.rollback()
            for id in sessions:
                login=db.get(LoginSession,id)
                if login:login.revoked_at=datetime.now(timezone.utc)
            db.commit()
    return 0 if report.get('status')=='passed' else 1

if __name__=='__main__':raise SystemExit(main())
