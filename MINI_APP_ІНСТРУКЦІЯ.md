# 🚀 MINI APP - ПОВНА ІНСТРУКЦІЯ

## 📋 Що було додано?

1. **Mini App кнопка в боті** - стартує веб-додаток прямо в Telegram
2. **HTML Фронтенд** (`mini_app.html`) - красивий інтерфейс з усіма функціями
3. **Flask Бекенд** (`app.py`) - API для синхронізації даних з БД

---

## 🏗️ АРХІТЕКТУРА

```
┌─────────────────────────────────┐
│   📱 Telegram Mini App          │
│   (встроєний в Telegram)        │
└──────────────┬──────────────────┘
               │
               ↓
┌─────────────────────────────────┐
│   🌐 Фронтенд (HTML/JS)         │
│   mini_app.html                 │
│   - Красивий UI                 │
│   - Завдання, таймери, записки  │
│   - Профіль, статистика         │
└──────────────┬──────────────────┘
               │
               ↓
┌─────────────────────────────────┐
│   🔌 API (Flask)                │
│   app.py - localhost:5000       │
│   - GET/POST endpoints          │
│   - Синхронізація з БД          │
└──────────────┬──────────────────┘
               │
               ↓
┌─────────────────────────────────┐
│   💾 База даних (SQLite)        │
│   bot_data.db                   │
│   - Завдання                    │
│   - Таймери                     │
│   - Записки                     │
│   - Користувачі                 │
└─────────────────────────────────┘
```

---

## ⚙️ ВСТАНОВЛЕННЯ

### 1️⃣ **Встанови Flask та CORS**

```bash
pip install flask flask-cors
```

### 2️⃣ **Запусти Бекенд (API сервер)**

```bash
python app.py
```

Побачиш:
```
============================================================
🚀 COUPLE BOT API ЗАПУЩЕНО!
============================================================
📡 Сервер: http://localhost:5000
💾 База даних: bot_data.db
🔌 CORS увімкнений
============================================================

✅ Доступні endpoints:
   GET  /api/health - перевірка стану
   GET  /api/todos/<user_id> - завдання
   POST /api/todos/add - додати завдання
   ...
```

### 3️⃣ **Запусти Telegram Бота (в іншому терміналі)**

```bash
python telegram_bot_couples.py
```

### 4️⃣ **Запусти Фронтенд**

Простий спосіб - запусти локальний веб-сервер:

```bash
# Python 3.x
python -m http.server 8000

# Або з Node.js
npx http-server
```

Або просто відкрий `mini_app.html` в браузері!

---

## 📱 ЯК ВИКОРИСТОВУВАТИ

### У Telegram боті:

1. Натисни кнопку **"🚀 ВІДКРИТИ ДОДАТОК"** в меню
2. Відкриється веб-додаток **прямо в Telegram**
3. Можеш переглядати дані і додавати нові

### Функції:

- **🏠 Головна** - статистика та наступний таймер
- **📋 Завдання** - додай та переглядай завдання
- **⏳ Таймери** - створюй таймери до важливих дат
- **💝 Записки** - пиши любовні записки
- **👤 Профіль** - інформація про тебе

---

## 🌐 API ENDPOINTS

### Перевірка стану

```
GET http://localhost:5000/api/health
```

Відповідь:
```json
{
  "status": "OK",
  "message": "Couple Bot API працює!",
  "database": "bot_data.db"
}
```

### Завдання

```
GET /api/todos/<user_id>
GET /api/todos/<user_id>/<todo_id>/toggle
POST /api/todos/add
```

Приклад:
```json
POST /api/todos/add
{
  "user_id": 123456789,
  "title": "Написати листа",
  "notes": ""
}
```

### Таймери

```
GET /api/timers/<user_id>
POST /api/timers/add
```

Приклад:
```json
POST /api/timers/add
{
  "user_id": 123456789,
  "event": "Зустріч",
  "target_date": "2025-04-15"
}
```

### Записки

```
GET /api/notes/<user_id>
POST /api/notes/add
```

### Синхронізація

```
GET /api/sync/<user_id>
```

Отримує ВСЕ дані користувача!

---

## 🚀 РОЗГОРТАННЯ НА ПРОДАКШН

### Варіант 1: Heroku (рекомендується)

```bash
# 1. Встанови Heroku CLI
# 2. Створи акаунт на heroku.com

# 3. Логінся
heroku login

# 4. Створи додаток
heroku create your-couple-bot-api

# 5. Запусти
git push heroku main

# 6. Отримай URL
heroku info your-couple-bot-api
```

### Варіант 2: Vercel (для фронтенда)

```bash
# 1. Встанови Vercel CLI
npm install -g vercel

# 2. Запусти
vercel
```

### Варіант 3: Railway, Render, Replit

Всі підтримують Python + Flask

---

## 📝 ОНОВЛЕННЯ URL В БОТІ

Коли розгорнеш на продакшні, онови URL в `telegram_bot_couples.py`:

```python
def main_keyboard():
    web_app_url = "https://your-frontend-url.vercel.app"  # ← ОБНОВИ!
    
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 ВІДКРИТИ ДОДАТОК", web_app=WebAppInfo(url=web_app_url))],
        ...
    ])
```

Також в `mini_app.html` оновити API URL:

```javascript
// Для локального тестування
const API_URL = "http://localhost:5000/api";

// Для продакшену
const API_URL = "https://your-api-url.herokuapp.com/api";
```

---

## 🔧 СТРУКТУРА ФАЙЛІВ

```
📁 Проект
├── telegram_bot_couples.py    (Telegram бот)
├── app.py                      (Flask API)
├── mini_app.html               (Фронтенд)
├── bot_data.db                 (База даних)
├── БАЗА_ДАННЫХ_SQLite.md       (Документація БД)
├── COMMAND_MENU_BOTFATHER.md   (Документація команд)
└── ... інші файли
```

---

## 🧪 ТЕСТУВАННЯ

### 1️⃣ Перевір здоров'я API

```bash
curl http://localhost:5000/api/health
```

### 2️⃣ Отримай твої завдання

```bash
curl http://localhost:5000/api/todos/123456789
```

Замість `123456789` введи свій Telegram ID

### 3️⃣ Додай завдання

```bash
curl -X POST http://localhost:5000/api/todos/add \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 123456789,
    "title": "Тестове завдання",
    "notes": ""
  }'
```

---

## ⚠️ ВИРІШЕННЯ ПРОБЛЕМ

### Проблема: "Cannot GET /api/todos/..."

**Розв'язання:**
- Перевір чи запущено Flask (`python app.py`)
- Перевір чи вірний URL в JavaScript

### Проблема: "CORS error"

**Розв'язання:**
- Переконайся що `flask-cors` встановлено
- `CORS(app)` включено в `app.py`

### Проблема: "Database is locked"

**Розв'язання:**
- Закрий SQLite Browser якщо відкритий
- Перезапусти Flask

### Проблема: Mini App не відкривається

**Розв'язання:**
- Перевір `web_app_url` в `main_keyboard()`
- Переконайся що веб-сервер запущено

---

## 🎯 НАСТУПНІ КРОКИ

1. ✅ Запусти все локально та тестуй
2. ✅ Розгорни бекенд на Heroku/Railway
3. ✅ Розгорни фронтенд на Vercel/Netlify
4. ✅ Онови URL в боті
5. ✅ Тестуй в реальному Telegram
6. ✅ Додай нові функції

---

## 💡 ПОРАДИ

- 📱 Mini App відкривається **прямо в Telegram** - красивіше ніж кнопки!
- 🔄 Дані **синхронізуються** між ботом і додатком автоматично
- 💾 Все зберігається в **SQLite БД** - дані безпечні
- 🚀 Легко розгорнути на **Heroku** за 5 хвилин

---

## 📚 ФАЙЛИ

- `telegram_bot_couples.py` - Telegram бот з Mini App кнопкою
- `app.py` - Flask API сервер
- `mini_app.html` - Веб-додаток (фронтенд)

---

**Готово! Твій Telegram бот тепер має красивий веб-додаток! 🎉**
