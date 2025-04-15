@echo off
call venv\Scripts\activate
python email_sender.py
pause
deactivate