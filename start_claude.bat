@echo off
title Lanzador OmniRoute + Claude Code
color 0A

echo [1/2] Configurando variables para desviar el trafico hacia OmniRoute...
cd /d C:\Users\DEEL\OneDrive\Desktop\Laboratorio

:: Apunta Claude Code a tu servidor local de OmniRoute en el puerto 20128
set ANTHROPIC_BASE_URL=http://localhost:20128

:: Llave ficticia o token para evitar que Claude Code pida inicio de sesión oficial
set ANTHROPIC_API_KEY=omniroute-local-key

:: Si prefieres usar un perfil generado específico en lugar del combo global, descomenta la siguiente línea:
:: set CLAUDE_CONFIG_DIR=C:\Users\DEEL\.claude\profiles\ds-deepseek-v4-flash-high

echo [2/2] Iniciando Claude Code...
claude

pause