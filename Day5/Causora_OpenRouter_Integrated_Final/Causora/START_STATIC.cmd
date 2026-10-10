@echo off
cd /d "%~dp0"
powershell -NoProfile -File scripts\start-day5.ps1 -Mode static
if errorlevel 1 pause
