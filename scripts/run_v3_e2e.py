"""Launch an isolated DB and the built SPA, then execute browser acceptance tests."""
import os,sys,subprocess,tempfile,socket,time,urllib.request,argparse
from pathlib import Path
from process_control import stop_process_tree,uvicorn_command

ROOT=Path(__file__).resolve().parents[1]
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--approved-roster',action='store_true')
    args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='manshi-v3-') as directory:
        assert Path(directory).resolve().parent==Path(tempfile.gettempdir()).resolve()
        env=dict(os.environ,DATABASE_PATH=str(Path(directory)/'e2e.sqlite3'),SESSION_SECRET_KEY='isolated-browser-test-secret-more-than-32-chars',APP_SERVE_STATIC='true',COOKIE_SECURE='false',INITIAL_DATA_MODE='roster' if args.approved_roster else 'empty')
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        env['E2E_BASE_URL']=f'http://127.0.0.1:{port}'
        for command in [['-m','alembic','upgrade','head'],['-m','app.scripts.init_data']]:
            subprocess.run([sys.executable,*command],cwd=ROOT/'backend',env=env,check=True)
        log=(ROOT/'docs/v3-e2e-server.log').open('w',encoding='utf-8')
        server=subprocess.Popen(uvicorn_command('app.main:app','--host','127.0.0.1','--port',str(port)),cwd=ROOT/'backend',env=env,stdout=log,stderr=log)
        try:
            for attempt in range(100):
                if server.poll() is not None:raise RuntimeError('测试服务启动失败，请查看 docs/v3-e2e-server.log')
                try:
                    with urllib.request.urlopen(env['E2E_BASE_URL']+'/api/health',timeout=1):break
                except OSError:time.sleep(.1)
            else:raise RuntimeError('测试服务启动超时')
            result=subprocess.run(['node','tests/initial-data-e2e.mjs' if args.approved_roster else 'tests/v3-e2e.mjs'],cwd=ROOT/'frontend',env=env)
        finally:
            stop_process_tree(server);log.close()
        return result.returncode

if __name__=='__main__':raise SystemExit(main())
