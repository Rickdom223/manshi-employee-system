"""Create a private source + consistent SQLite snapshot package for CloudStudio."""
import argparse
from contextlib import closing
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import zipfile
from zoneinfo import ZoneInfo

from package_project import included
from verify_cloud_data import inspect_database, readonly, verify

ROOT = Path(__file__).resolve().parents[1]


def snapshot(source, target):
    source, target = Path(source).resolve(), Path(target).resolve()
    if source == target or target.exists():
        raise ValueError('必须使用新的备份路径，禁止覆盖现有数据库')
    with closing(readonly(source)) as live, closing(sqlite3.connect(target)) as saved:
        live.backup(saved)
    before = inspect_database(target)
    # Only the independent cloud copy is changed; retain every business/account row.
    with closing(sqlite3.connect(target)) as saved:
        saved.execute('PRAGMA secure_delete=ON')
        saved.execute('DELETE FROM sessions')
        saved.commit()
        saved.execute('VACUUM')
    if inspect_database(target) != before:
        raise ValueError('备份中的业务数据发生改变')
    return before


def summary(database):
    with closing(readonly(database)) as db:
        result = {name: db.execute('SELECT count(*) FROM "' + name + '"').fetchone()[0]
                  for name in ['employees', 'users', 'departments', 'punch_records',
                               'attendance_rules', 'leave_requests', 'salaries']}
        result['staff_status'] = dict(db.execute('SELECT status,count(*) FROM employees GROUP BY status'))
        result['roles'] = dict(db.execute('SELECT role,count(*) FROM users GROUP BY role'))
        return result


def build(source, output):
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('迁移包已存在，请指定新文件名，避免覆盖旧备份')
    stamp = datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(timespec='seconds')
    # The private staging directory is never selected by the source-only packager.
    with tempfile.TemporaryDirectory(prefix='.runtime-cloud-migration-', dir=ROOT) as directory:
        database = Path(directory)/'manshi.sqlite3'
        tables = snapshot(source, database)
        manifest = {'format_version': 1, 'exported_at': stamp,
                    'database_sha256': hashlib.sha256(database.read_bytes()).hexdigest(),
                    'tables': tables, 'summary': summary(database),
                    'sessions': 'cleared in cloud snapshot only; account passwords unchanged'}
        manifest_path = Path(directory)/'manifest.json'
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        verify(database, manifest_path)
        secrets = []
        env_file = ROOT/'backend/.env'
        if env_file.exists():
            for line in env_file.read_text(encoding='utf-8').splitlines():
                if line.startswith(('SESSION_SECRET_KEY=', 'JWT_SECRET_KEY=', 'APP_SECRET_KEY=', 'INITIAL_ADMIN_PASSWORD=')):
                    value = line.split('=', 1)[1]
                    if value and not value.startswith('REPLACE_'):
                        secrets.append(value.encode())
        candidate = Path(directory)/'candidate.zip'
        with zipfile.ZipFile(candidate, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for path in ROOT.rglob('*'):
                if not path.is_file() or not included(path) or 'migration' in path.relative_to(ROOT).parts:
                    continue
                data = path.read_bytes()
                if any(secret in data for secret in secrets):
                    raise ValueError('拒绝打包含有环境密钥的源码文件：' + str(path.relative_to(ROOT)))
                archive.writestr((Path(ROOT.name)/path.relative_to(ROOT)).as_posix(), data)
            archive.write(database, ROOT.name+'/backend/data/manshi.sqlite3')
            archive.write(manifest_path, ROOT.name+'/migration/manifest.json')
        with zipfile.ZipFile(candidate) as archive:
            names = archive.namelist()
            if archive.testzip() is not None or any(name.endswith('/.env') for name in names):
                raise ValueError('迁移包校验失败')
            for required in ['start.sh', 'scripts/cloudstudio_start.py', 'frontend/.env.example', '.vscode/preview.yml']:
                if ROOT.name+'/'+required not in names:
                    raise ValueError('迁移包缺少一键启动文件：'+required)
            db_name = ROOT.name+'/backend/data/manshi.sqlite3'
            if hashlib.sha256(archive.read(db_name)).hexdigest() != manifest['database_sha256']:
                raise ValueError('迁移包中的数据库与备份不一致')
        # Exclusive creation prevents an accidental overwrite of a previous export.
        with output.open('xb') as destination, candidate.open('rb') as source_file:
            import shutil
            shutil.copyfileobj(source_file, destination)
    return {'package': str(output), 'exported_at': stamp, 'summary': manifest['summary'],
            'verified_tables': len(tables), 'bytes': output.stat().st_size,
            'database_sha256': manifest['database_sha256']}


def main():
    parser = argparse.ArgumentParser(description='导出当前全部业务数据和源码；不修改本机数据库')
    parser.add_argument('--database', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.database is None:
        sys.path.insert(0, str(ROOT/'backend'))
        from app.core.config import database_path
        args.database = database_path()
    stamp = datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y%m%d-%H%M%S')
    output = args.output or ROOT.parent/f'manshi-cloud-current-data-{stamp}.zip'
    print(json.dumps(build(args.database, output), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
