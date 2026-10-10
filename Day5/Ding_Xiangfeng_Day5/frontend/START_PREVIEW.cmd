@echo off
setlocal
cd /d "%~dp0"
set "CAUSORA_NODE=node"
where node >nul 2>nul
if errorlevel 1 set "CAUSORA_NODE=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
if not "%CAUSORA_NODE%"=="node" if not exist "%CAUSORA_NODE%" (
  echo Node.js 22 is required. See README.md.
  pause
  exit /b 1
)
if not exist "out\index.html" (
  echo Build missing. Run npm ci then npm run check before opening this preview.
  pause
  exit /b 1
)
set CAUSORA_FRONTEND_MODE=static
set CAUSORA_STATIC_ONLY=true
set NEXT_PUBLIC_CAUSORA_STATIC_ONLY=true
set HOST=127.0.0.1
if not defined PORT set PORT=3000
echo Open http://127.0.0.1:%PORT% after the server starts.
echo Keep this window open. Ctrl+C stops the preview.
"%CAUSORA_NODE%" scripts\serve-static.mjs
if errorlevel 1 pause
