@echo off
call venv\Scripts\activate

python telegram_bot.py || (
    echo.
    echo [ERROR] Python script exited with error code %errorlevel%
)

call deactivate
pause