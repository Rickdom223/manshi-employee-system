"""Cross-platform development launcher with controlled shutdown of both services."""
import argparse,os,shutil,socket,subprocess,sys,time
from pathlib import Path
import httpx
from process_control import uvicorn_command,stop_process_tree

ROOT=Path(__file__).resolve().parents[1]
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--backend-port',type=int,default=8000)
    parser.add_argument('--web-port',type=int,default=3000)
    parser.add_argument('--check-startup',action='store_true',help='启动两项服务并检查代理，然后关闭本次服务')
    args=parser.parse_args()
    node=shutil.which('node')
    if not node or not (ROOT/'frontend/node_modules/vite/bin/vite.js').exists():raise SystemExit('请先安装Node依赖：cd frontend，然后 npm ci')
    for port in [args.backend_port,args.web_port]:
        with socket.socket() as sock:
            try:sock.bind(('127.0.0.1',port))
            except OSError:raise SystemExit(f'端口 {port} 已占用，请先停止原项目服务或使用其他端口')
    subprocess.run([sys.executable,'-m','app.scripts.init_db'],cwd=ROOT/'backend',check=True)
    env=dict(os.environ,API_PROXY_TARGET=f'http://127.0.0.1:{args.backend_port}')
    flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
    runtime=ROOT/'deploy/runtime';runtime.mkdir(parents=True,exist_ok=True)
    backend_log=(runtime/'backend-dev.log').open('a',encoding='utf-8')
    web_log=(runtime/'frontend-dev.log').open('a',encoding='utf-8')
    backend=web=None
    try:
        backend=subprocess.Popen(uvicorn_command('app.main:app','--host','127.0.0.1','--port',str(args.backend_port)),cwd=ROOT/'backend',env=env,creationflags=flags,stdout=backend_log,stderr=backend_log)
        for _ in range(100):
            if backend.poll() is not None:raise RuntimeError('后端启动失败')
            try:
                if httpx.get(f'http://127.0.0.1:{args.backend_port}/api/health',timeout=1,trust_env=False).status_code==200:break
            except httpx.HTTPError:pass
            time.sleep(.1)
        else:raise RuntimeError('后端启动超时，请查看 deploy/runtime/backend-dev.log')
        web=subprocess.Popen([node,'node_modules/vite/bin/vite.js','--host','0.0.0.0','--port',str(args.web_port)],cwd=ROOT/'frontend',env=env,creationflags=flags,stdout=web_log,stderr=web_log)
        print(f'打开 http://127.0.0.1:{args.web_port}；Ctrl+C停止本次启动的服务。',flush=True)
        if args.check_startup:
            for _ in range(100):
                try:
                    if httpx.get(f'http://127.0.0.1:{args.web_port}/api/health',timeout=1,trust_env=False).status_code==200:return
                except httpx.HTTPError:pass
                time.sleep(.1)
            raise RuntimeError('前端同源代理未就绪')
        while web.poll() is None and backend.poll() is None:time.sleep(.2)
    except KeyboardInterrupt:pass
    finally:
        for process in [web,backend]:
            if process:stop_process_tree(process)
        backend_log.close();web_log.close()

if __name__=='__main__':main()
