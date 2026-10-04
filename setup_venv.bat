@echo off
if not exist .venv (
    py -3.12 -m venv .venv
    if errorlevel 1 exit /b 1
)
.venv\Scripts\python.exe -c "import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) else 'Python 3.12 is required; recreate .venv.')"
if errorlevel 1 exit /b %ERRORLEVEL%
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
exit /b %ERRORLEVEL%