"""Data migration must retain business values, ignore sessions, and detect corruption."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
from package_current_data import snapshot
from verify_cloud_data import inspect_database, verify


def test_wal_snapshot_keeps_data_and_local_sessions(tmp_path):
    source, target = tmp_path/'source.sqlite3', tmp_path/'cloud.sqlite3'
    with closing(sqlite3.connect(source)) as live:
        live.execute('PRAGMA journal_mode=WAL')
        live.execute('CREATE TABLE employees(id INTEGER PRIMARY KEY,name TEXT,salary INTEGER)')
        live.execute('CREATE TABLE sessions(id INTEGER PRIMARY KEY,token_hash TEXT)')
        live.execute('INSERT INTO employees VALUES(31,?,300000)', ('新增员工',))
        live.execute("INSERT INTO sessions VALUES(1,'local-session')")
        live.commit()  # Keep connection open: the newest committed rows are in WAL.
        before = inspect_database(source)
        assert snapshot(source, target) == before
        assert inspect_database(source) == inspect_database(target) == before
        assert live.execute('SELECT count(*) FROM sessions').fetchone()[0] == 1
        with closing(sqlite3.connect(target)) as cloud:
            assert cloud.execute('SELECT count(*) FROM sessions').fetchone()[0] == 0
            assert cloud.execute('SELECT name,salary FROM employees').fetchone() == ('新增员工', 300000)
        with pytest.raises(ValueError):
            snapshot(source, target)  # No overwriting an existing database.
        with pytest.raises(ValueError):
            snapshot(source, source)


def test_verification_rejects_changed_business_rows(tmp_path):
    database = tmp_path/'cloud.sqlite3'
    with closing(sqlite3.connect(database)) as db:
        db.execute('CREATE TABLE employees(id INTEGER PRIMARY KEY,name TEXT)')
        db.execute("INSERT INTO employees VALUES(1,'original')")
        db.commit()
    manifest = tmp_path/'manifest.json'
    manifest.write_text(json.dumps({'format_version': 1, 'tables': inspect_database(database),
                                   'exported_at': '2026-10-28', 'summary': {'employees': 1}}), encoding='utf-8')
    assert verify(database, manifest)['result'] == 'passed'
    with closing(sqlite3.connect(database)) as db:
        db.execute("UPDATE employees SET name='changed'")
        db.commit()
    with pytest.raises(ValueError, match='employees'):
        verify(database, manifest)
