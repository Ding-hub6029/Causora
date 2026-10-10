@echo off
cd /d "%~dp0"
powershell -NoProfile -File scripts\setup-windows.ps1
pause
