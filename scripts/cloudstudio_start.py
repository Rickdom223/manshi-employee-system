"""Install, preserve data, and supervise the two CloudStudio development services."""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import sqlite3
import subprocess
import sys
import threading
import time
from urllib.error import URLError, HTTPError
from urllib.parse import urlsplit
from urllib.request import build_opener, ProxyHandler, Request
import uuid

from process_control import stop_process_tree, uvicorn_command
from verify_cloud_data import verify

ROOT = Path(__file__).resolve().parents[1]


def run(command, cwd, env, capture=False):
    result = subprocess.run([str(v) for v in command], cwd=cwd, env=env, check=True,
                            text=True, encoding='utf-8', stdout=subprocess.PIPE if capture else None)
    return result.stdout.strip() if capture else ''


def tools_available(env):
    if sys.version_info < (3, 11):
        raise RuntimeError('需要 Python 3.11 或以上版本')
    node = shutil.which('node', path=env.get('PATH'))
    if not node:
        raise RuntimeError('缺少 Node.js 22.12+，请选择包含 Python 和 Node.js 的工作空间')
    version = run([node, '--version'], ROOT, env, capture=True)
    match = re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)', version)
    if not match or tuple(map(int, match.groups())) < (22, 12, 0):
        raise RuntimeError(f'Node.js 版本为 {version}，需要 22.12 或以上版本')
    npm_cli = next((path for path in [Path(node).parent/'node_modules/npm/bin/npm-cli.js',
                                    Path(node).parent.parent/'node_modules/npm/bin/npm-cli.js']
                    if path.is_file()), None)
    npm_path = shutil.which('npm', path=env.get('PATH'))
    if not npm_cli and npm_path and (Path(npm_path).parent/'npm-cli.js').is_file():
        npm_cli = Path(npm_path).parent/'npm-cli.js'
    npm = [node, str(npm_cli)] if npm_cli else [npm_path]
    if not npm[0]:
        raise RuntimeError('缺少 npm，请使用带 npm 的 Node.js 环境')
    run([*npm, '--version'], ROOT, env, capture=True)
    return node, npm


def preview_origin(env, port, supplied=None):
    value = supplied or env.get('CLOUDSTUDIO_PREVIEW_URL', '')
    if not value and all(env.get(k) for k in ('X_IDE_SPACE_KEY', 'X_IDE_SPACE_REGION', 'X_IDE_SPACE_HOST')):
        value = f"https://{env['X_IDE_SPACE_KEY']}--{port}.{env['X_IDE_SPACE_REGION']}.{env['X_IDE_SPACE_HOST']}"
    if not value:
        return None
    parts = urlsplit(value)
    try:
        valid_port = parts.port
    except ValueError:
        raise ValueError('预览地址端口不正确') from None
    if (parts.scheme not in {'http', 'https'} or not parts.hostname or parts.username or parts.password
            or parts.path not in {'', '/'} or parts.query or parts.fragment
            or not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?', parts.hostname)
            or (valid_port is not None and not 1 <= valid_port <= 65535)):
        raise ValueError('预览地址必须为完整的 http(s)://域名，可带端口，不带路径或通配符')
    return f'{parts.scheme}://{parts.netloc}'.rstrip('/')


def free_ports(backend_port, web_port):
    if backend_port == web_port:
        raise ValueError('前后端端口不能相同')
    for port, host in [(backend_port, '127.0.0.1'), (web_port, '0.0.0.0')]:
        if not 1 <= port <= 65535:
            raise ValueError('端口必须为 1–65535')
        with socket.socket() as sock:
            try:
                sock.bind((host, port))
            except OSError:
                raise RuntimeError(f'端口 {port} 已占用，请先停止原服务；不会抢占或自动换端口') from None


def backup_database(database, root):
    database = Path(database).resolve()
    if not database.exists():
        return None
    directory = root/'backend/backups'
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
    target = directory/f'before-cloud-start-{stamp}-{uuid.uuid4().hex[:8]}.sqlite3'
    with closing(sqlite3.connect(database.as_uri()+'?mode=ro', uri=True)) as original, closing(sqlite3.connect(target)) as saved:
        original.backup(saved)
        if saved.execute('PRAGMA integrity_check').fetchall() != [('ok',)] or saved.execute('PRAGMA foreign_key_check').fetchall():
            raise RuntimeError('数据库备份检查失败，已停止启动')
    return target


def prepare(root, env, npm, skip_install=False):
    python = root/('backend/.venv/Scripts/python.exe' if os.name == 'nt' else 'backend/.venv/bin/python')
    if not python.is_file():
        if (root/'backend/.venv').exists():
            raise RuntimeError('虚拟环境与当前系统不匹配，请使用不含本机 .venv 的迁移包')
        if skip_install:
            raise RuntimeError('未安装后端依赖，首次启动不要使用 --skip-install')
        print('[1/5] 创建 Python 虚拟环境', flush=True)
        run([sys.executable, '-m', 'venv', root/'backend/.venv'], root, env)
    if not skip_install:
        print('[1/5] 安装后端依赖', flush=True)
        run([python, '-m', 'pip', 'install', '-r', root/'backend/requirements.txt'], root, env)
    run([python, '-c', 'import fastapi,uvicorn,sqlalchemy,alembic,dotenv,pwdlib'], root, env)
    print('[2/5] 检查配置和现有数据', flush=True)
    run([python, '-m', 'app.scripts.setup_env'], root/'backend', env)
    frontend_env = root/'frontend/.env'
    if not frontend_env.exists():
        with frontend_env.open('x', encoding='utf-8') as output:
            output.write((root/'frontend/.env.example').read_text(encoding='utf-8'))
    code = ('import json,os;from app.core.config import database_path,secret_key,token_minutes;'
            'secret_key();token_minutes();print(json.dumps({"database":str(database_path()),'
            '"origins":os.getenv("ALLOWED_ORIGINS","")}))')
    config = json.loads(run([python, '-c', code], root/'backend', env, capture=True))
    manifest_path = root/'migration/manifest.json'
    marker = None
    if manifest_path.is_file():
        if Path(config['database']).resolve() != (root/'backend/data/manshi.sqlite3').resolve():
            raise RuntimeError('迁移包必须使用自带的 backend/data/manshi.sqlite3，请检查数据库路径配置')
        digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        marker = root/'backend/data'/f'.cloudstudio-import-{digest}.verified'
        if not marker.exists():
            verify(config['database'], manifest_path)
            print('已核对迁移清单，现有业务数据完整', flush=True)
    saved = backup_database(config['database'], root)
    if saved:
        print(f'现有数据库备份：{saved.relative_to(root)}', flush=True)
    run([python, '-m', 'app.scripts.init_db'], root/'backend', env)
    if marker and not marker.exists():
        marker.write_text('首次导入已核对；后续新增数据保留。\n', encoding='utf-8')
    print('[3/5] 检查前端依赖', flush=True)
    if not skip_install:
        stamp = hashlib.sha256((root/'frontend/package-lock.json').read_bytes()
                               + (root/'frontend/package.json').read_bytes()
                               + run(['node', '--version'], root, env, capture=True).encode()).hexdigest()
        installed = root/'frontend/node_modules/.cloudstudio-dependencies'
        if not installed.is_file() or installed.read_text(encoding='utf-8') != stamp:
            run([*npm, 'ci'], root/'frontend', env)
            installed.write_text(stamp, encoding='utf-8')
    if not (root/'frontend/node_modules/vite/bin/vite.js').is_file():
        raise RuntimeError('前端依赖不完整，首次启动不要使用 --skip-install')
    return python, config['origins']


def service_command(python, port, root, env):
    arguments = ('app.main:app', '--host', '127.0.0.1', '--port', str(port))
    # POSIX virtualenv executables may symlink to the system binary. Preserve
    # the venv invocation path so its installed dependencies remain available.
    if os.name != 'nt':
        return [str(python), '-m', 'uvicorn', *arguments]
    if Path(python).resolve() == Path(sys.executable).resolve():
        return uvicorn_command(*arguments)
    runtime = json.loads(run([python, '-c', 'import sys,sysconfig,json;print(json.dumps([sys._base_executable,sysconfig.get_path("purelib")]))'], root, env, capture=True))
    bootstrap = f'import sys,runpy;sys.path.insert(0,{runtime[1]!r});runpy.run_module("uvicorn",run_name="__main__")'
    return [runtime[0], '-c', bootstrap, *arguments]


def serve(root, python, node, env, backend_port=8000, web_port=3000, check_startup=False):
    runtime = root/'deploy/runtime'
    runtime.mkdir(parents=True, exist_ok=True)
    opener = build_opener(ProxyHandler({}))
    stopped = threading.Event()
    old_handlers = {}
    processes = []
    if threading.current_thread() is threading.main_thread():
        for sig in (signal.SIGINT, signal.SIGTERM):
            old_handlers[sig] = signal.signal(sig, lambda *_: stopped.set())

    def request(path, through_web=False):
        headers = {}
        if through_web and env.get('CLOUDSTUDIO_PREVIEW_HOST'):
            headers['Host'] = env['CLOUDSTUDIO_PREVIEW_HOST']
        port = web_port if through_web else backend_port
        return opener.open(Request(f'http://127.0.0.1:{port}{path}', headers=headers), timeout=1)

    def healthy(through_web=False):
        until = time.monotonic()+30
        while time.monotonic() < until:
            if stopped.is_set():
                raise InterruptedError('已停止启动')
            if any(p.poll() is not None for p in processes):
                raise RuntimeError('服务启动失败，请查看 deploy/runtime/cloudstudio-*.log')
            try:
                with request('/api/health', through_web) as response:
                    if response.status == 200 and json.load(response)['data']['status'] == 'ok':
                        return
            except (URLError, TimeoutError, ValueError):
                stopped.wait(.15)
        raise RuntimeError('服务未能就绪，请查看 deploy/runtime/cloudstudio-*.log')

    try:
        with (runtime/'cloudstudio-backend.log').open('a', encoding='utf-8') as backend_log, (runtime/'cloudstudio-frontend.log').open('a', encoding='utf-8') as web_log:
            print(f'[4/5] 启动后端 {backend_port}', flush=True)
            processes.append(subprocess.Popen(service_command(python, backend_port, root, env), cwd=root/'backend', env=env, stdout=backend_log, stderr=backend_log))
            healthy()
            print(f'[5/5] 启动前端 {web_port}', flush=True)
            processes.append(subprocess.Popen([node, 'node_modules/vite/bin/vite.js', '--host', '0.0.0.0', '--port', str(web_port), '--strictPort'], cwd=root/'frontend', env=env, stdout=web_log, stderr=web_log))
            healthy(through_web=True)
            with request('/my/attendance', True) as response:
                if '<div id="app">' not in response.read().decode():
                    raise RuntimeError('网页入口检查失败')
            try:
                request('/api/me/attendance?month='+datetime.now(timezone.utc).strftime('%Y-%m'), True)
            except HTTPError as error:
                if error.code != 401:
                    raise RuntimeError('前后端认证代理检查失败') from error
            else:
                raise RuntimeError('前后端认证代理检查失败')
            print('启动成功：满氏吉他制琴有限公司企业员工管理系统', flush=True)
            print(f'网页：{env.get("CLOUDSTUDIO_PREVIEW_URL") or f"http://127.0.0.1:{web_port}"}', flush=True)
            print(f'CloudStudio 请选择 {web_port} 端口预览；API 文档位于同一网址的 /api/docs。', flush=True)
            print('按 Ctrl+C 停止本次启动的前后端服务。', flush=True)
            if check_startup:
                return
            while not stopped.wait(.2):
                if any(p.poll() is not None for p in processes):
                    raise RuntimeError('服务意外退出，已停止另一个服务，请检查启动日志')
    finally:
        try:
            for process in reversed(processes):
                try:
                    stop_process_tree(process)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
        finally:
            for sig, handler in old_handlers.items():
                signal.signal(sig, handler)


def main():
    parser = argparse.ArgumentParser(description='CloudStudio 一键安装并启动员工管理系统，保留现有数据')
    parser.add_argument('--backend-port', type=int, default=8000)
    parser.add_argument('--web-port', type=int, default=3000)
    parser.add_argument('--preview-url', help='平台实际 HTTPS 预览地址，通常由 CloudStudio 环境自动识别')
    parser.add_argument('--check', action='store_true', help='只检查环境，不安装、不修改数据库')
    parser.add_argument('--skip-install', action='store_true', help='依赖已安装时跳过安装')
    parser.add_argument('--prepare-only', action='store_true', help='完成安装、配置和数据准备后退出')
    parser.add_argument('--check-startup', action='store_true', help='实际启动并检查网页和API代理，然后停止本次服务')
    args = parser.parse_args()
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    node, npm = tools_available(env)
    origin = preview_origin(env, args.web_port, args.preview_url)
    if not args.prepare_only:
        free_ports(args.backend_port, args.web_port)
    if args.check:
        print('环境检查通过：Python、Node.js、npm 和端口可用；尚未安装或启动。')
        return
    python, allowed = prepare(ROOT, env, npm, args.skip_install)
    env.update(API_PROXY_TARGET=f'http://127.0.0.1:{args.backend_port}', APP_SERVE_STATIC='false')
    if origin:
        parts = urlsplit(origin)
        env.update(CLOUDSTUDIO_PREVIEW_URL=origin, CLOUDSTUDIO_PREVIEW_HOST=parts.hostname,
                   CLOUDSTUDIO_HMR_PROTOCOL='wss' if parts.scheme == 'https' else 'ws',
                   CLOUDSTUDIO_HMR_PORT=str(parts.port or (443 if parts.scheme == 'https' else 80)),
                   ALLOWED_ORIGINS=','.join(dict.fromkeys([*filter(None, allowed.split(',')), origin])))
        if parts.scheme == 'https':
            env.setdefault('COOKIE_SECURE', 'true')
    if args.prepare_only:
        print('配置和数据准备完成；运行 sh start.sh 启动。')
        return
    serve(ROOT, python, node, env, args.backend_port, args.web_port, args.check_startup)


if __name__ == '__main__':
    try:
        main()
    except (InterruptedError, KeyboardInterrupt):
        print('已停止本次启动。')
    except (RuntimeError, ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f'启动未完成：{error}', file=sys.stderr)
        sys.exit(1)
