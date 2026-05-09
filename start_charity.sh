#!/bin/bash

# Скрипт для запуску сайту благодійних фондів

echo "🚀 Запуск сайту благодійних фондів..."

# Перевірка чи порт вільний
if lsof -Pi :5001 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  Порт 5001 зайнятий. Зупиняємо старий процес..."
    fuser -k 5001/tcp
    sleep 1
fi

# Запуск сервера
echo "📊 База даних: charity_funds.db"
echo "🌐 Локальний доступ: http://localhost:5001"
echo ""
echo "Натисніть Ctrl+C для зупинки"
echo "================================"

python3 charity_server.py
