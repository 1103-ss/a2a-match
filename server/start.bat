@echo off
echo ============================================
echo A2A Match Server MVP
echo ============================================
echo.

cd /d "%~dp0"

echo Installing dependencies...
pip install -r requirements.txt -q

echo.
echo Starting server...
echo API: http://localhost:5000
echo Health: http://localhost:5000/api/v1/health
echo.
echo Press Ctrl+C to stop
echo ============================================

python a2a_server.py
