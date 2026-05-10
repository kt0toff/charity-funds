#!/bin/bash

# Скрипт для запуску сайту благодійних фондів з ngrok тунелем

echo "🚀 Запуск сайту благодійних фондів з публічним доступом..."

# Перевірка чи порт вільний
if lsof -Pi :5001 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  Порт 5001 зайнятий. Зупиняємо старий процес..."
    fuser -k 5001/tcp
    sleep 1
fi

# Зупинка старих ngrok процесів
pkill -f "ngrok.*5001" 2>/dev/null

# Запуск сервера у фоні
echo "📊 База даних: charity_funds.db"
python3 charity_server.py &
SERVER_PID=$!

# Чекаємо поки сервер запуститься
echo "⏳ Очікування запуску сервера..."
sleep 3

# Перевірка чи сервер запустився
if ! lsof -Pi :5001 -sTCP:LISTEN -t >/dev/null ; then
    echo "❌ Помилка: сервер не запустився"
    exit 1
fi

echo "✅ Сервер запущено"
echo "🌐 Локальний доступ: http://localhost:5001"
echo ""

# Запуск ngrok
echo "🔗 Створення публічного посилання через ngrok..."
ngrok http 5001 --log=stdout > /tmp/charity_ngrok.log 2>&1 &
NGROK_PID=$!

# Чекаємо поки ngrok запуститься
sleep 3

# Отримуємо публічний URL
PUBLIC_URL=$(curl -s http://localhost:4040/api/tunnels | grep -o '"public_url":"https://[^"]*' | grep -o 'https://[^"]*' | head -1)

if [ -n "$PUBLIC_URL" ]; then
    echo ""
    echo "================================"
    echo "✅ Публічне посилання активне!"
    echo ""
    echo "📱 Поділіться цим посиланням:"
    echo "   $PUBLIC_URL"
    echo ""
    echo "🌐 Локальний доступ:"
    echo "   http://localhost:5001"
    echo "================================"
else
    echo "⚠️  Не вдалося отримати публічне посилання"
    echo "   Сайт доступний локально: http://localhost:5001"
fi

echo ""
echo "Натисніть Ctrl+C для зупинки"
echo ""

# Функція для коректного завершення
cleanup() {
    echo ""
    echo "🛑 Зупинка сервісів..."
    kill $SERVER_PID 2>/dev/null
    kill $NGROK_PID 2>/dev/null
    pkill -f "ngrok.*5001" 2>/dev/null
    echo "✅ Все зупинено"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Чекаємо
wait
