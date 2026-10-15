#!/bin/sh
cd "$(dirname "$0")"
if [ -z "$OPENAI_API_KEY" ]; then
  printf 'Optional: enter your OpenAI API key for AI chat (leave blank for local styling): '
  stty -echo 2>/dev/null || true
  read OPENAI_API_KEY
  stty echo 2>/dev/null || true
  printf '\n'
  export OPENAI_API_KEY
fi
exec python3 app_server.py
