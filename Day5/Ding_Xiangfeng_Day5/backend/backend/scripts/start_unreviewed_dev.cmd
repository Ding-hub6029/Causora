@echo off
setlocal
set "ROOT=%~dp0.."
if not defined CAUSORA_PYTHON set "CAUSORA_PYTHON=python"
"%CAUSORA_PYTHON%" "%ROOT%\scripts\start_unreviewed_dev.py" %*
endlocal
