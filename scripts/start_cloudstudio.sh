#!/usr/bin/env sh
# 保留原入口，统一使用项目根目录的一键启动。
set -eu
case "$0" in
  */*) SCRIPT_DIR=${0%/*} ;;
  *) SCRIPT_DIR=. ;;
esac
PROJECT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
exec sh "$PROJECT_DIR/start.sh" "$@"
