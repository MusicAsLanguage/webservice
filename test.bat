@echo off
.venv\Scripts\python.exe -m pytest --cov --cov-report=term-missing %*
exit /b %ERRORLEVEL%