@echo off
set PYTHONPATH=%cd%
call venv\Scripts\activate
python modules\email_sender.py
pause
deactivate