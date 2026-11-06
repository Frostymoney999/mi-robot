@echo off
cd /d "%~dp0"
python -m pip install -r requirements.txt
echo.
echo Listo. Prueba: python robot.py todo --demo
pause
