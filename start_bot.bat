@echo off
cd /d %~dp0
.venv\Scripts\activate
python telegram_bot_aiogram.py
pause

