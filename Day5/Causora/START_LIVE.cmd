@echo off
cd /d "%~dp0"
powershell -NoProfile -File scripts\start-day5.ps1 -Mode live
if errorlevel 1 pause
