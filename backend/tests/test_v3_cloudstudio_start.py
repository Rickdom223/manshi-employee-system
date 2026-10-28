"""Cloud startup must preserve data, validate origins, and own its service lifecycle."""
from contextlib import closing
import json
import os
from pathlib import Path
import socket
import sqlite3
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
import cloudstudio_start as launcher


def test_exact_preview_origin_from_platform():
    env = {'X_IDE_SPACE_KEY': 'space123', 'X_IDE_SPACE_REGION': 'ap-shanghai2',
           'X_IDE_SPACE_HOST': 'cloudstudio.club'}
    assert launcher.preview_origin(env, 3000) == 'https://space123--3000.ap-shanghai2.cloudstudio.club'
    assert launcher.preview_origin(env, 4000, 'https://actual.example:8443/') == 'https://actual.example:8443'
    assert launcher.preview_origin({}, 3000) is None
    for invalid in ['https://*.example', 'https://user:pass@example', 'https://example/path',
                    'https://example?secret=1', 'https://example#fragment', 'file:///tmp/file',
                    'https://example:99999']:
        with pytest.raises(ValueError):
            launcher.preview_origin({}, 3000, invalid)


def test_occupied_port_does_not_replace_other_service():
    with socket.socket() as existing:
        existing.bind(('127.0.0.1', 0))
        existing.listen()
        occupied = existing.getsockname()[1]
        with pytest.raises(RuntimeError, match='已占用'):
            launcher.free_ports(occupied, 3000)
        assert existing.getsockname()[1] == occupied
    with pytest.raises(ValueError):
        launcher.free_ports(3000, 3000)


def test_online_backup_preserves_wal_and_password_values(tmp_path):
    source = tmp_path/'live.sqlite3'
    with closing(sqlite3.connect(source)) as db:
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('CREATE TABLE users(id INTEGER PRIMARY KEY,password TEXT)')
        db.execute("INSERT INTO users VALUES(1,'existing-password-hash')")
        db.commit()
        target = launcher.backup_database(source, tmp_path)
        assert target != source
        with closing(sqlite3.connect(target)) as saved:
            assert saved.execute('SELECT * FROM users').fetchall() == db.execute('SELECT * FROM users').fetchall()
        assert db.execute('SELECT count(*) FROM users').fetchone()[0] == 1
    assert launcher.backup_database(tmp_path/'missing.sqlite3', tmp_path) is None


def make_project(root):
    (root/'backend/.venv'/('Scripts' if os.name == 'nt' else 'bin')).mkdir(parents=True)
    python = root/('backend/.venv/Scripts/python.exe' if os.name == 'nt' else 'backend/.venv/bin/python')
    python.touch()
    (root/'frontend/node_modules/vite/bin').mkdir(parents=True)
    (root/'frontend/node_modules/vite/bin/vite.js').touch()
    (root/'frontend/.env.example').write_text('VITE_API_BASE_URL=/api\n', encoding='utf-8')
    (root/'frontend/package-lock.json').write_text('{}', encoding='utf-8')
    (root/'frontend/package.json').write_text('{}', encoding='utf-8')
    return python


def test_automatic_dependencies_and_existing_config_survive(tmp_path, monkeypatch):
    python = make_project(tmp_path)
    frontend_env = tmp_path/'frontend/.env'
    frontend_env.write_text('# preserve custom settings\nVITE_API_BASE_URL=/api\n', encoding='utf-8')
    calls = []
    def fake_run(command, cwd, env, capture=False):
        calls.append([str(v) for v in command])
        if capture and command[-1] == '--version':
            return 'v24.22.1'
        if capture:
            return json.dumps({'database': str(tmp_path/'missing.sqlite3'), 'origins': 'https://existing.example'})
        return ''
    monkeypatch.setattr(launcher, 'run', fake_run)
    result = launcher.prepare(tmp_path, {}, ['npm'])
    assert result == (python, 'https://existing.example')
    assert any('pip' in call and 'install' in call for call in calls)
    assert ['npm', 'ci'] in calls
    assert any('app.scripts.setup_env' in call for call in calls)
    assert any('app.scripts.init_db' in call for call in calls)
    assert frontend_env.read_text(encoding='utf-8').startswith('# preserve custom settings')
    calls.clear()
    launcher.prepare(tmp_path, {}, ['npm'])
    assert ['npm', 'ci'] not in calls
    (tmp_path/'frontend/package-lock.json').write_text('{"changed":true}', encoding='utf-8')
    launcher.prepare(tmp_path, {}, ['npm'])
    assert ['npm', 'ci'] in calls


def test_failed_frontend_stops_started_backend(tmp_path, monkeypatch):
    commands, stopped = [], []
    class Process:
        def __init__(self, *args, **kwargs):
            self.number = len(commands)
            commands.append(args[0])
        def poll(self):
            return 1 if self.number == 1 else None
    class Response:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return b'{"data":{"status":"ok"}}'
    class Opener:
        def open(self, *args, **kwargs): return Response()
    monkeypatch.setattr(launcher.subprocess, 'Popen', Process)
    monkeypatch.setattr(launcher, 'service_command', lambda *args: ['backend'])
    monkeypatch.setattr(launcher, 'stop_process_tree', stopped.append)
    monkeypatch.setattr(launcher, 'build_opener', lambda *args: Opener())
    with pytest.raises(RuntimeError, match='启动失败'):
        launcher.serve(tmp_path, sys.executable, 'node', {}, check_startup=True)
    assert [p.number for p in stopped] == [1, 0]


def test_import_verified_once_and_later_data_survives(tmp_path, monkeypatch):
    from verify_cloud_data import inspect_database
    make_project(tmp_path)
    database = tmp_path/'backend/data/manshi.sqlite3'
    database.parent.mkdir()
    with closing(sqlite3.connect(database)) as db:
        db.execute('CREATE TABLE employees(id INTEGER PRIMARY KEY,name TEXT)')
        db.execute("INSERT INTO employees VALUES(31,'new employee')")
        db.commit()
    (tmp_path/'migration').mkdir()
    manifest = tmp_path/'migration/manifest.json'
    manifest.write_text(json.dumps({'format_version': 1, 'tables': inspect_database(database),
                                   'summary': {'employees': 1}, 'exported_at': '2026-10-28'}), encoding='utf-8')
    def fake_run(command, cwd, env, capture=False):
        if capture:
            return json.dumps({'database': str(database), 'origins': ''})
        return ''
    monkeypatch.setattr(launcher, 'run', fake_run)
    launcher.prepare(tmp_path, {}, ['npm'], skip_install=True)
    assert len(list(database.parent.glob('.cloudstudio-import-*.verified'))) == 1
    with closing(sqlite3.connect(database)) as db:
        db.execute("INSERT INTO employees VALUES(32,'added after import')")
        db.commit()
    launcher.prepare(tmp_path, {}, ['npm'], skip_install=True)
    with closing(sqlite3.connect(database)) as db:
        assert db.execute('SELECT count(*) FROM employees').fetchone()[0] == 2


def test_reject_modified_first_import_before_initialization(tmp_path, monkeypatch):
    from verify_cloud_data import inspect_database
    make_project(tmp_path)
    database = tmp_path/'backend/data/manshi.sqlite3'
    database.parent.mkdir()
    with closing(sqlite3.connect(database)) as db:
        db.execute('CREATE TABLE employees(id INTEGER PRIMARY KEY)')
    (tmp_path/'migration').mkdir()
    (tmp_path/'migration/manifest.json').write_text(json.dumps({'format_version': 1, 'tables': inspect_database(database),
                                                             'summary': {}, 'exported_at': '2026-10-28'}), encoding='utf-8')
    with closing(sqlite3.connect(database)) as db:
        db.execute('INSERT INTO employees VALUES(1)')
        db.commit()
    calls = []
    def fake_run(command, cwd, env, capture=False):
        calls.append(command)
        return json.dumps({'database': str(database), 'origins': ''}) if capture else ''
    monkeypatch.setattr(launcher, 'run', fake_run)
    with pytest.raises(ValueError, match='employees'):
        launcher.prepare(tmp_path, {}, ['npm'], skip_install=True)
    assert not any('app.scripts.init_db' in command for command in calls)
