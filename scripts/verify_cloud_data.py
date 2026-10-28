"""Verify an imported snapshot before its first login; never modify the database."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]


def readonly(path):
    return sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)


def quote(name):
    return '"' + name.replace('"', '""') + '"'


def inspect_database(path):
    with closing(readonly(path)) as db:
        db.execute('BEGIN')
        if db.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
            raise ValueError('数据库完整性检查失败')
        if db.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('数据库关联关系检查失败')
        tables = {}
        for name, schema in db.execute("SELECT name,sql FROM sqlite_master WHERE type='table' ORDER BY name").fetchall():
            if name == 'sessions':
                continue  # Cloud logins must be independent of local logins.
            columns = [row[1] for row in db.execute('PRAGMA table_info(' + quote(name) + ')')]
            rows = sorted(json.dumps(row, ensure_ascii=False, separators=(',', ':'),
                                     default=lambda v: {'bytes': v.hex()})
                          for row in db.execute('SELECT * FROM ' + quote(name)))
            digest = hashlib.sha256()
            for value in [schema, columns, *rows]:
                digest.update(json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode())
                digest.update(b'\n')
            tables[name] = {'rows': len(rows), 'sha256': digest.hexdigest()}
        return tables


def verify(database, manifest_path):
    manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    if manifest.get('format_version') != 1:
        raise ValueError('迁移清单版本不受支持')
    actual = inspect_database(database)
    expected = manifest['tables']
    changed = sorted(name for name in set(actual) | set(expected) if actual.get(name) != expected.get(name))
    if changed:
        raise ValueError('以下表与导出时不同：' + ', '.join(changed))
    return {'verified_tables': len(actual), 'exported_at': manifest['exported_at'],
            'summary': manifest['summary'], 'result': 'passed'}


def main():
    parser = argparse.ArgumentParser(description='首次登录前核对迁移数据，仅检查、不修改')
    parser.add_argument('--database', type=Path, default=ROOT/'backend/data/manshi.sqlite3')
    parser.add_argument('--manifest', type=Path, default=ROOT/'migration/manifest.json')
    args = parser.parse_args()
    print(json.dumps(verify(args.database, args.manifest), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
