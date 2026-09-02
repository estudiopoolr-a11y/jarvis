@echo off
start cmd /k "fcc-server"
timeout /t 3 /nobreak > nul

set ANTHROPIC_BASE_URL=http://localhost:8082/v1
set ANTHROPIC_AUTH_TOKEN=fcc_local_token
set CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1

call claude
pause