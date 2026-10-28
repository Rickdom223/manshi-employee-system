#!/usr/bin/env sh
# CloudStudio 一键启动；兼容教程中的 sh start.sh 和 bash start.sh。
set -eu
case "$0" in
  */*) SCRIPT_DIR=${0%/*} ;;
  *) SCRIPT_DIR=. ;;
esac
PROJECT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR" && pwd)
for PYTHON_COMMAND in python3 python; do
  if command -v "$PYTHON_COMMAND" >/dev/null 2>&1 && "$PYTHON_COMMAND" -c 'import sys;sys.exit(sys.version_info < (3, 11))' >/dev/null 2>&1; then
    exec "$PYTHON_COMMAND" "$PROJECT_DIR/scripts/cloudstudio_start.py" "$@"
  fi
done
echo '缺少可用的 Python 3.11+，请选择包含 Python 和 Node.js 的工作空间。' >&2
exit 1
