@echo off
chcp 65001 >nul
title Сайт благодійних фондів

echo ========================================
echo 🚀 Запуск сайту благодійних фондів
echo ========================================
echo.

REM Перевірка чи Python встановлено
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не знайдено!
    echo Встановіть Python з https://www.python.org/
    pause
    exit /b 1
)

REM Перевірка чи Flask встановлено
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo 📦 Встановлення Flask...
    pip install flask flask-cors
)

REM Перевірка чи порт 5001 вільний
netstat -ano | findstr ":5001" >nul
if not errorlevel 1 (
    echo ⚠️  Порт 5001 зайнятий. Зупиняємо старий процес...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5001"') do (
        taskkill /F /PID %%a >nul 2>&1
    )
    timeout /t 2 /nobreak >nul
)

echo.
echo 📊 База даних: charity_funds.db
echo 🌐 Локальний доступ: http://localhost:5001
echo.
echo Натисніть Ctrl+C для зупинки
echo ========================================
echo.

REM Запуск сервера
python charity_server.py

pause
