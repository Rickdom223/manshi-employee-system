import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from collections import OrderedDict
from threading import Lock
from time import monotonic
from pwdlib import PasswordHash
from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import secret_key
from app.core.database import get_db
from app.core.errors import fail
from app.models import User, LoginSession, Employee

password_hash = PasswordHash.recommended()
dummy_hash = password_hash.hash(secrets.token_urlsafe(32))
COOKIE = 'manshi_session'

def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()

def csrf_for(token):
    return hmac.new(secret_key().encode(), token.encode(), hashlib.sha256).hexdigest()

def check_origin(request):
    allowed = os.getenv('ALLOWED_ORIGINS', 'http://127.0.0.1:3000,http://localhost:3000,http://127.0.0.1:8080,http://localhost:8080').split(',')
    origin = request.headers.get('origin', '')
    same_origin = origin in {f'http://{request.headers.get("host")}', f'https://{request.headers.get("host")}'}
    if not same_origin and origin not in [v.strip() for v in allowed]:
        fail(403, 'ORIGIN_DENIED', '请求来源不受信任，请检查部署来源配置')

def current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get(COOKIE, '')
    session = db.scalar(select(LoginSession).where(LoginSession.token_hash == digest(token))) if token else None
    if not session or session.revoked_at or session.expires_at.replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc):
        fail(401, 'UNAUTHORIZED', '登录已失效，请重新登录')
    user = db.get(User, session.user_id)
    if not user or not user.is_active:
        fail(401, 'UNAUTHORIZED', '登录已失效，请重新登录')
    if user.employee_id and db.get(Employee, user.employee_id).status != 'active':
        fail(401, 'UNAUTHORIZED', '员工账号已停用')
    request.state.login_session = session
    if request.method in {'POST','PUT','PATCH','DELETE'}:
        check_origin(request)
        if not hmac.compare_digest(digest(request.headers.get('x-csrf-token', '')), session.csrf_token_hash):
            fail(403, 'CSRF_FAILED', '安全校验失败，请刷新页面后重试')
    return user

def require_admin(user: User = Depends(current_user)):
    if user.role != 'SYS_ADMIN':
        fail(403, 'FORBIDDEN', '仅管理员可执行此操作')
    return user

def require_employee(user: User = Depends(current_user)):
    if not user.employee_id:
        fail(403, 'FORBIDDEN', '仅员工账号可访问')
    return user

def create_session(db, user, response):
    token = secrets.token_urlsafe(48)
    csrf = csrf_for(token)
    hours = int(os.getenv('SESSION_EXPIRE_HOURS', '8'))
    if not 1 <= hours <= 168:
        raise RuntimeError('SESSION_EXPIRE_HOURS须为1–168')
    db.add(LoginSession(token_hash=digest(token), user_id=user.id, csrf_token_hash=digest(csrf), expires_at=datetime.now(timezone.utc)+timedelta(hours=hours)))
    db.commit()
    response.set_cookie(COOKIE, token, max_age=hours*3600, httponly=True, secure=os.getenv('COOKIE_SECURE','false').lower()=='true', samesite='lax', path='/')
    return csrf

def public_user(user, csrf, db=None):
    personal=['SELF_PROFILE','SELF_ATTENDANCE','SELF_LEAVE','SELF_SALARY'] if user.employee_id else []
    grants={'EMPLOYEE':[], 'SUPERVISOR':['DEPARTMENT_EMPLOYEES_READ','DEPARTMENT_LEAVE_REVIEW'], 'HR':['EMPLOYEE_MANAGE','POSITION_MANAGE','ATTENDANCE_MANAGE','ALL_LEAVES_READ','SALARY_MANAGE','HR_DASHBOARD'], 'SYS_ADMIN':['USER_MANAGE','SUPERVISOR_ASSIGN','HR_BOOTSTRAP','AUDIT_READ']}
    employee=db.get(Employee,user.employee_id) if db and user.employee_id else None
    basic=dict(id=employee.id,name=employee.full_name,employee_no=employee.employee_no,department_id=employee.department_id,position_id=employee.position_id,status='ACTIVE' if employee.status=='active' else 'LEFT') if employee else None
    return {'id':user.id, 'username':user.username, 'role':user.role, 'employee_id':user.employee_id, 'employee':basic, 'permissions':['DEPARTMENTS_READ','POSITIONS_READ']+personal+grants[user.role], 'display_name':user.display_name, 'csrf_token':csrf}

def require_hr(user: User = Depends(current_user)):
    if user.role != 'HR':
        fail(403, 'FORBIDDEN', '仅 HR 可执行此操作')
    return user

def require_supervisor(user: User = Depends(current_user)):
    if user.role != 'SUPERVISOR':
        fail(403, 'FORBIDDEN', '仅部门主管可执行此操作')
    return user

class LoginLimiter:
    def __init__(self):
        self.entries = OrderedDict()
        self.lock = Lock()
    def check(self, key):
        now = monotonic()
        with self.lock:
            times = [t for t in self.entries.pop(key, []) if now-t < 60]
            if len(times) >= 10:
                self.entries[key] = times
                fail(429, 'LOGIN_RATE_LIMIT', '登录请求过于频繁，请一分钟后重试')
            self.entries[key] = times
            while len(self.entries)>10000:
                self.entries.popitem(last=False)
    def failure(self, key):
        with self.lock:
            self.entries.setdefault(key, []).append(monotonic())
limiter = LoginLimiter()
