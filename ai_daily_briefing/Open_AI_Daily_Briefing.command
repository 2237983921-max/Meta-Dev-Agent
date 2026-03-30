#!/bin/zsh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if ! /usr/bin/env python3 "$SCRIPT_DIR/launch_briefing.py"; then
  echo
  echo "启动失败，按回车关闭窗口。"
  read
fi
