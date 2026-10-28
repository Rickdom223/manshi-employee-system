"""Build and verify a source-only ZIP with docs; exclude all runtime secrets."""
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {'.git', '.venv', '.tools', 'node_modules', 'dist', '__pycache__', '.pytest_cache', 'backups', 'test-results', 'data','runtime'}

def included(path):
    relative = path.relative_to(ROOT)
    return not any(part in EXCLUDED or part.startswith(('.test-run-','.runtime-')) for part in relative.parts) and path.name not in {'.env','npm-runtime.tgz','nginx.generated.conf','chart-diagnostic.png','debug-chart.mjs'} and not path.name.endswith('failure.png') and path.suffix not in {'.db', '.sqlite3', '.log', '.pyc', '.zip','.pid'} and not path.name.endswith(('.sqlite3-wal', '.sqlite3-shm'))

def main():
    output = ROOT.parent / 'manshi-employee-system-initial-data-20261028.zip'
    paths = [p for p in ROOT.rglob('*') if p.is_file() and included(p)]
    # Scan generated environment secrets in source bytes before publishing.
    env_path = ROOT / 'backend/.env'
    secrets = []
    if env_path.exists():
        for line in env_path.read_text(encoding='utf-8').splitlines():
            if line.startswith(('SESSION_SECRET_KEY=', 'JWT_SECRET_KEY=', 'APP_SECRET_KEY=', 'INITIAL_ADMIN_PASSWORD=')):
                value = line.split('=', 1)[1]
                if value and not value.startswith('REPLACE_'):
                    secrets.append(value.encode())
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in paths:
            data = path.read_bytes()
            if any(secret in data for secret in secrets):
                raise RuntimeError(f'拒绝打包含有环境秘密的文件：{path.relative_to(ROOT)}')
            archive.writestr((Path(ROOT.name) / path.relative_to(ROOT)).as_posix(), data)
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        names = set(archive.namelist())
        for required in ['README.md', 'start.sh', 'scripts/cloudstudio_start.py', 'backend/.env.example', 'frontend/.env.example', 'frontend/package-lock.json', '.vscode/preview.yml', 'scripts/start_cloudstudio.sh', 'checklist.md']:
            assert str(Path(ROOT.name) / required).replace('\\', '/') in names
        assert not any(name.endswith('/.env') or '/node_modules/' in name or '/.venv/' in name or name.endswith('.sqlite3') for name in names)
    print(f'源码包已校验：{len(paths)}个文件，{output.stat().st_size}字节，无环境秘密/数据库/本机依赖。')
    print(output)

if __name__ == '__main__':
    main()
