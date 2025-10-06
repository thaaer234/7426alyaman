@echo off
setlocal
chcp 65001 >nul
title Django Server

@REM REM ضع مسار مشروعك هنا
@REM set "PROJECT_DIR=C:\Users\THAAER\Desktop\اكرم طباعة"

@REM cd /d "%PROJECT_DIR%" || (echo [ERROR] المجلد غير موجود: %PROJECT_DIR% & pause & exit /b)

REM جرّب python ثم py
set "PY="
where python >nul 2>nul && set "PY=python"
if not defined PY where py >nul 2>nul && set "PY=py"
if not defined PY (echo [ERROR] Python غير موجود. & pause & exit /b)

REM افتح المتصفح ثم شغّل السيرفر
start "" "http://127.0.0.1:8000/ar/login/?next=/ar/"
"%PY%" manage.py runserver 127.0.0.1:8000
