@echo off
if not exist .venv (
    py -3.14 -m venv .venv
    if errorlevel 1 exit /b 1
)
.venv\Scripts\python.exe -c "import sys, sysconfig; sys.exit(0 if sys.version_info[:2] == (3, 14) and not sysconfig.get_config_var('Py_GIL_DISABLED') else 'Standard (GIL-enabled) Python 3.14 is required; recreate .venv.')"
if errorlevel 1 exit /b %ERRORLEVEL%
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
exit /b %ERRORLEVEL%