@echo off
setlocal
cd /d "%~dp0"
set "CAUSORA_NODE=node"
where node >nul 2>nul
if errorlevel 1 set "CAUSORA_NODE=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
if not "%CAUSORA_NODE%"=="node" if not exist "%CAUSORA_NODE%" (
  echo Please install Node.js 22.16 or newer before starting this preview.
  echo See README.md for instructions.
  pause
  exit /b 1
)
set HOST=127.0.0.1
set PORT=3000
echo Open http://127.0.0.1:3000 in your browser after the server starts.
echo Keep this window open. Press Ctrl+C to stop the preview.
"%CAUSORA_NODE%" scripts\serve-static.mjs
if errorlevel 1 pause
