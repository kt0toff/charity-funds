#!/bin/bash

echo "=== Testing Bot Startup Sequence ==="
echo ""

# Перевірка чи Flask запущений
echo "1. Checking if Flask is running..."
if curl -s http://127.0.0.1:5000/api/pc/status > /dev/null 2>&1; then
    echo "   ✅ Flask is responding"
else
    echo "   ❌ Flask is not responding"
fi

echo ""

# Перевірка ngrok
echo "2. Checking ngrok status..."
if pgrep -x "ngrok" > /dev/null; then
    echo "   ✅ ngrok process is running"

    # Отримуємо URL з ngrok API
    NGROK_URL=$(curl -s http://127.0.0.1:4040/api/tunnels | grep -o '"public_url":"https://[^"]*' | head -1 | cut -d'"' -f4)
    if [ ! -z "$NGROK_URL" ]; then
        echo "   ✅ ngrok URL: $NGROK_URL"
    else
        echo "   ⚠️  Could not get ngrok URL"
    fi
else
    echo "   ❌ ngrok is not running"
fi

echo ""

# Перевірка процесів ботів
echo "3. Checking bot processes..."
if pgrep -f "telegram_bot_couples.py" > /dev/null; then
    echo "   ✅ Couple Bot is running"
else
    echo "   ❌ Couple Bot is not running"
fi

if pgrep -f "remote_bot.py" > /dev/null; then
    echo "   ✅ PC Control Bot is running"
else
    echo "   ❌ PC Control Bot is not running"
fi

echo ""
echo "=== Test Complete ==="
