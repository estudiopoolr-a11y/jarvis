@echo off
set OPENAI_API_BASE=http://localhost:20128/v1
set OPENAI_API_KEY=cualquier_texto
echo Iniciando Codex con la pasarela local de OmniRoute...
codex --profile auto-best-coding
pause