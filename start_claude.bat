@echo off
title JARVIS - OmniRoute + Claude Code

echo Levantando servidor OmniRoute en segundo plano...
start /min "" omniroute

timeout /t 3 /nobreak >nul

set ANTHROPIC_BASE_URL=http://127.0.0.1:20128
set ANTHROPIC_API_KEY=omniroute
set CLAUDE_CODE_DISABLE_UNKNOWN_MODEL_WINDOW_ENFORCEMENT=1

echo Conectando Claude Code a OmniRoute...
claude --model auto