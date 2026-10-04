@echo off
if not exist .venv python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
exit /b %ERRORLEVEL%