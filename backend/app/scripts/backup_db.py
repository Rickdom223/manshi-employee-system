"""Online SQLite backup into a new file. Restore only to a separate target."""
import argparse
import sqlite3
from contextlib import closing
from pathlib import Path
from app.core.config import database_path

def main():
    parser = argparse.ArgumentParser(description='SQLite 在线备份，不覆盖现有文件')
    parser.add_argument('target', type=Path)
    args = parser.parse_args()
    target = args.target.resolve()
    if target.exists():
        parser.error('目标已存在，拒绝覆盖')
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with closing(sqlite3.connect(f'{database_path().as_uri()}?mode=ro', uri=True)) as source, closing(sqlite3.connect(target)) as destination:
            source.backup(destination)
            if destination.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise RuntimeError('备份完整性检查失败')
    except Exception:
        if target.exists():
            target.unlink()
        raise
    print('备份完整性检查通过。备份包含人员信息，不可公开提交。')

if __name__ == '__main__':
    main()
