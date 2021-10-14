rmdir /Q /S .venv
python -3 -m venv .venv
.venv\scripts\activate
pip install -r requirements.txt