from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import current_user, password_hash, dummy_hash, limiter, check_origin, create_session, public_user, csrf_for, COOKIE
from app.core.errors import fail
from app.models import User, LoginSession
from app.schemas import Login, Input, Name
from pydantic import Field, ConfigDict
import re

router = APIRouter(prefix='/api/auth')

def valid_password(value):
    if len(value) > 128 or not all(re.search(p, value) for p in ['[A-Z]','[a-z]','[0-9]']):
        fail(422, 'PASSWORD_RULE', '新密码须含 ASCII 大写字母、小写字母和数字，最多128字符')
    return value

class PasswordChange(Input):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=False)
    old_password: str = Field(max_length=256)
    new_password: str = Field(max_length=128)
    confirm_password: str = Field(max_length=128)

class ProfileChange(Input):
    display_name: Name

@router.post('/login')
def login(body: Login, request: Request, response: Response, db: Session = Depends(get_db)):
    check_origin(request)
    if request.headers.get('content-type','').split(';')[0] != 'application/json':
        fail(415,'JSON_REQUIRED','请使用JSON请求')
    limiter.check('ip:'+(request.client.host if request.client else 'unknown'))
    limiter.check('user:'+body.username.strip())
    user = db.scalar(select(User).where(User.username == body.username.strip()))
    valid = password_hash.verify(body.password, user.password_hash if user else dummy_hash)
    from app.models import Employee
    if not user or not valid or not user.is_active or (user.employee_id and db.get(Employee,user.employee_id).status != 'active'):
        limiter.failure('ip:'+(request.client.host if request.client else 'unknown'))
        limiter.failure('user:'+body.username.strip())
        fail(401, 'INVALID_CREDENTIALS', '用户名或密码错误')
    from app.core.security import digest
    old = request.cookies.get(COOKIE)
    if old:
        db.execute(update(LoginSession).where(LoginSession.token_hash==digest(old)).values(revoked_at=datetime.now(timezone.utc)))
    user.last_login_at = datetime.now(timezone.utc)
    csrf = create_session(db, user, response)
    return {'data': public_user(user, csrf, db)}

@router.get('/me')
def me(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return {'data': public_user(user, csrf_for(request.cookies[COOKIE]), db)}

@router.post('/logout')
def logout(request: Request, response: Response, user: User = Depends(current_user), db: Session = Depends(get_db)):
    request.state.login_session.revoked_at = datetime.now(timezone.utc)
    db.commit()
    response.delete_cookie(COOKIE, path='/')
    return {'data': {'logged_out': True}}

@router.put('/password')
@router.post('/change-password')
def password(body: PasswordChange, request: Request, response: Response, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not password_hash.verify(body.old_password, user.password_hash):
        fail(400,'WRONG_PASSWORD','旧密码不正确')
    valid_password(body.new_password)
    if body.new_password != body.confirm_password:
        fail(422,'PASSWORD_MISMATCH','两次新密码不一致')
    if body.new_password == body.old_password:
        fail(422,'SAME_PASSWORD','新密码不能与旧密码相同')
    user.password_hash = password_hash.hash(body.new_password)
    db.execute(update(LoginSession).where(LoginSession.user_id==user.id).values(revoked_at=datetime.now(timezone.utc)))
    db.commit()
    response.delete_cookie(COOKIE, path='/')
    return {'data': {'changed': True}}

@router.patch('/profile')
def profile(body: ProfileChange, user: User = Depends(current_user), db: Session = Depends(get_db)):
    user.display_name = body.display_name
    db.commit()
    return {'data': {'display_name': user.display_name}}
