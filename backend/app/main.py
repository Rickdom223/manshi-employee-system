from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy import text
from app.core.config import secret_key, token_minutes
from app.core.database import engine

@asynccontextmanager
async def lifespan(app):
    secret_key()
    token_minutes()
    yield

app = FastAPI(title='满氏吉他制琴有限公司企业员工管理系统', lifespan=lifespan, docs_url='/api/docs', redoc_url=None, openapi_url='/api/openapi.json')
from app.routers.auth import router as auth_router
app.include_router(auth_router)
from app.routers.v3_people import router as people_router
app.include_router(people_router)
from app.routers.v3_business import router as business_router
app.include_router(business_router)
from app.routers.v3_dashboard import router as hr_dashboard_router
app.include_router(hr_dashboard_router)

@app.exception_handler(StarletteHTTPException)
async def http_error(request, exc):
    detail = exc.detail if isinstance(exc.detail, dict) else {'code': 'HTTP_ERROR', 'message': str(exc.detail)}
    return JSONResponse({'error': detail}, status_code=exc.status_code, headers=exc.headers)

@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    fields = ', '.join('.'.join(str(x) for x in e['loc'][1:]) for e in exc.errors())
    return JSONResponse({'error': {'code': 'VALIDATION_ERROR', 'message': f'字段校验失败：{fields}'}}, status_code=422)

@app.exception_handler(Exception)
async def unexpected_error(request, exc):
    return JSONResponse({'error': {'code': 'INTERNAL_ERROR', 'message': '服务暂时不可用，请稍后重试'}}, status_code=500)

from sqlalchemy.exc import IntegrityError
@app.exception_handler(IntegrityError)
async def integrity_error(request, exc):
    return JSONResponse({'error':{'code':'CONFLICT','message':'记录重复或关联关系冲突，请检查编号及生效日期'}},status_code=409)

@app.get('/health')
@app.get('/api/health')
def health():
    with engine.connect() as connection:
        connection.execute(text('SELECT 1'))
    return {'data': {'status': 'ok'}}

# Explicit fallback for environments without a reverse proxy. API errors never become SPA HTML.
import os
if os.getenv('APP_SERVE_STATIC','false').lower()=='true':
    from pathlib import Path
    from fastapi.responses import FileResponse
    from app.core.config import BACKEND
    static_root=(BACKEND.parent/'frontend'/'dist').resolve()
    @app.get('/{path:path}',include_in_schema=False)
    def spa(path:str):
        if path=='api' or path.startswith('api/'):
            raise HTTPException(404,detail='API不存在')
        target=(static_root/path).resolve()
        if not target.is_relative_to(static_root):raise HTTPException(404)
        if target.is_file():return FileResponse(target)
        if Path(path).suffix:raise HTTPException(404)
        if not (static_root/'index.html').is_file():raise HTTPException(503,detail='请先构建前端')
        return FileResponse(static_root/'index.html')
