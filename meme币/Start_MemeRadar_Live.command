#!/bin/zsh

cd /Users/dutaorui/Desktop/codex || exit 1
/Users/dutaorui/Desktop/codex/.venv/bin/python -m uvicorn server:app --app-dir "/Users/dutaorui/Desktop/codex/meme币" --host 127.0.0.1 --port 8124
