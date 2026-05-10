"""
Telegram-бот для пари на відстані.

Встановлення:
    pip install "python-telegram-bot==22.7"

Запуск:
    python telegram_bot_couples.py

Функції:
    • Надсилання повідомлень за @username
    • 📋 Список завдань для двох
    • ⏳ Таймер до наступної зустрічі
    • 💝 Love Notes (любовні записки)
    • Блокування користувачів
    • Адмін-панель
"""

import logging
import sqlite3
import os
import uuid
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, WebAppInfo, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    InlineQueryHandler,
    ContextTypes,
    filters,
)

# ... (rest of imports)

# ─── Inline Mode ──────────────────────────────────────────────────────────────

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробник інлайн-запитів з логуванням"""
    try:
        query = update.inline_query.query
        user = update.inline_query.from_user
        logger.info(f"📥 Отримано інлайн-запит від {user.full_name} (@{user.username}): '{query}'")
        
        results = [
            InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title="🤗 Обійняти",
                description="Надіслати віртуальні обійми",
                input_message_content=InputTextMessageContent("🤗 Я міцно обіймаю тебе!"),
                thumbnail_url="https://emojicdn.elk.sh/🤗"
            ),
            InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title="💋 Цьом",
                description="Надіслати ніжний поцілунок",
                input_message_content=InputTextMessageContent("💋 Цьом! Думаю про тебе."),
                thumbnail_url="https://emojicdn.elk.sh/💋"
            ),
            InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title="💝 Швидка записка",
                description="Надіслати записку з вашим текстом",
                input_message_content=InputTextMessageContent(f"💝 {query}" if query else "💝 Я кохаю тебе!"),
                thumbnail_url="https://emojicdn.elk.sh/💝"
            ),
        ]
        
        await update.inline_query.answer(results, cache_time=1)
        logger.info(f"✅ Відповідь на інлайн-запит надіслана успішно.")
    except Exception as e:
        logger.error(f"❌ Помилка в інлайн-запиті: {e}", exc_info=True)

from dotenv import load_dotenv

load_dotenv()

# ─── Конфігурація ──────────────────────────────────────────────────────────────

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = set(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else set()
DB_PATH = os.getenv("DB_PATH", "bot_data.db")
WEB_APP_URL = os.getenv("WEB_APP_URL", "https://your-domain.com")  # Посилання на ваш сервер

if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не знайдено в .env файлі!")
    exit(1)

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════════════════════════════════════
# ═══════════════════ 💾 БАЗА ДАНИХ SQLite 💾 ═════════════════════════════════════
# ════════════════════════════════════════════════════════════════════════════════

def init_db():
    """Ініціалізує SQLite базу даних при запуску"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Таблиця користувачів
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            mood TEXT,
            anniversary_date TEXT,
            partner_id INTEGER
        )
    ''')
    
    # Міграція
    try: c.execute("ALTER TABLE users ADD COLUMN mood TEXT")
    except: pass
    try: c.execute("ALTER TABLE users ADD COLUMN mood_comment TEXT")
    except: pass
    try: c.execute("ALTER TABLE users ADD COLUMN anniversary_date TEXT")
    except: pass
    try: c.execute("ALTER TABLE users ADD COLUMN partner_id INTEGER")
    except: pass
    try: c.execute("ALTER TABLE users ADD COLUMN city TEXT")
    except: pass
    try: c.execute("ALTER TABLE users ADD COLUMN timezone TEXT")
    except: pass
    try: c.execute("ALTER TABLE users ADD COLUMN coins INTEGER DEFAULT 0")
    except: pass
    try: c.execute("ALTER TABLE users ADD COLUMN next_visit_date TEXT")
    except: pass

    # Таблиця купонів (Love Shop)
    c.execute('''
        CREATE TABLE IF NOT EXISTS coupons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            creator_id INTEGER,
            recipient_id INTEGER,
            title TEXT,
            price INTEGER,
            status TEXT DEFAULT 'available',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Таблиця тач-статусу (Digital Touch)
    c.execute('''
        CREATE TABLE IF NOT EXISTS touch_status (
            user_id INTEGER PRIMARY KEY,
            last_touch TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Таблиця календаря
    c.execute('''
        CREATE TABLE IF NOT EXISTS calendar_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            event_date TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Таблиця "Відкрий, коли..."
    c.execute('''
        CREATE TABLE IF NOT EXISTS open_when (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER,
            recipient_id INTEGER,
            category TEXT,
            content TEXT,
            unlock_date TEXT,
            is_opened INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Таблиця для ігор (Хрестики-нолики)
    c.execute('''
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player1_id INTEGER,
            player2_id INTEGER,
            board TEXT,
            turn_id INTEGER,
            winner_id INTEGER,
            status TEXT DEFAULT 'active'
        )
    ''')

    # Питання дня
    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT,
            day_offset INTEGER DEFAULT 0
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id INTEGER,
            user_id INTEGER,
            answer TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(question_id) REFERENCES daily_questions(id),
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    ''')
    
    # Таблиця завдань
    c.execute('''
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            notes TEXT,
            category TEXT DEFAULT 'Завдання',
            done INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    ''')

    try: c.execute("ALTER TABLE todos ADD COLUMN category TEXT DEFAULT 'Завдання'")
    except: pass
    
    # Таблиця таймерів
    c.execute('''
        CREATE TABLE IF NOT EXISTS timers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            event TEXT,
            target_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    ''')
    
    # Таблиця Love Notes
    c.execute('''
        CREATE TABLE IF NOT EXISTS love_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            note_text TEXT,
            recipient_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    ''')
    
    # Таблиця друзів
    c.execute('''
        CREATE TABLE IF NOT EXISTS friends (
            user_id INTEGER,
            friend_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(user_id, friend_id),
            FOREIGN KEY(user_id) REFERENCES users(user_id),
            FOREIGN KEY(friend_id) REFERENCES users(user_id)
        )
    ''')
    
    # Таблиця блокування
    c.execute('''
        CREATE TABLE IF NOT EXISTS blocked (
            user_id INTEGER,
            blocked_user_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(user_id, blocked_user_id),
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("✅ База даних ініціалізована!")


def save_user_to_db(user_id: int, username: str, full_name: str):
    """Зберігає користувача в БД"""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)", (user_id, username, full_name))
        c.execute("UPDATE users SET username = ?, full_name = ? WHERE user_id = ?", (username, full_name, user_id))
        conn.commit()
        conn.close()
        logger.info(f"User saved: {user_id} (@{username})")
    except sqlite3.Error as e:
        logger.error(f"Database error saving user {user_id}: {e}")
        raise

def save_todo_to_db(user_id: int, title: str, notes: str):
    """Зберігає завдання в БД"""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        c = conn.cursor()
        c.execute(
            "INSERT INTO todos (user_id, title, notes) VALUES (?, ?, ?)",
            (user_id, title, notes)
        )
        conn.commit()
        conn.close()
        logger.info(f"Todo saved for user {user_id}: {title}")
    except sqlite3.Error as e:
        logger.error(f"Database error saving todo: {e}")
        raise


def save_timer_to_db(user_id: int, event: str, target_date: str):
    """Зберігає таймер в БД"""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        c = conn.cursor()
        c.execute(
            "INSERT INTO timers (user_id, event, target_date) VALUES (?, ?, ?)",
            (user_id, event, target_date)
        )
        conn.commit()
        conn.close()
        logger.info(f"Timer saved for user {user_id}: {event}")
    except sqlite3.Error as e:
        logger.error(f"Database error saving timer: {e}")
        raise


def save_love_note_to_db(user_id: int, note_text: str, recipient_id: int = None):
    """Зберігає Love Note в БД"""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        c = conn.cursor()
        c.execute(
            "INSERT INTO love_notes (user_id, note_text, recipient_id) VALUES (?, ?, ?)",
            (user_id, note_text, recipient_id)
        )
        conn.commit()
        conn.close()
        logger.info(f"Love note saved from user {user_id}")
    except sqlite3.Error as e:
        logger.error(f"Database error saving love note: {e}")
        raise
    conn.close()


def save_friend_to_db(user_id: int, friend_id: int):
    """Зберігає друга в БД"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO friends (user_id, friend_id) VALUES (?, ?)",
        (user_id, friend_id)
    )
    conn.commit()
    conn.close()


def save_blocked_to_db(user_id: int, blocked_user_id: int):
    """Зберігає заблоковану людину в БД"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO blocked (user_id, blocked_user_id) VALUES (?, ?)",
        (user_id, blocked_user_id)
    )
    conn.commit()
    conn.close()

# ─── Стани ConversationHandler ─────────────────────────────────────────────────

SEND_RECIPIENT, SEND_MESSAGE = range(2)
REPLY_MESSAGE = 10
TODO_ADD_TITLE, TODO_ADD_NOTES = range(20, 22)
TIMER_SET_DATE, TIMER_SET_EVENT = range(30, 32)
LOVE_NOTE_TEXT = 40
LOVE_NOTE_RECIPIENT = 41
ADD_FRIEND_ID = 50
ADD_PARTNER_ID = 60

# ─── Сховище (в пам'яті) ───────────────────────────────────────────────────────
pending_replies: dict[int, dict] = {}


# ─── Допоміжні функції ─────────────────────────────────────────────────────────

def register(user) -> bool:
    if not user.username:
        return False
    save_user_to_db(user.id, user.username, user.full_name)
    return True


def get_user_friends(user_id: int) -> set:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT friend_id FROM friends WHERE user_id = ?", (user_id,))
    friends_set = {row[0] for row in c.fetchall()}
    conn.close()
    return friends_set


def get_user_timers(user_id: int) -> list:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    # Знаходимо партнера
    c.execute("SELECT partner_id FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    partner_id = row[0] if row else None
    
    if partner_id:
        c.execute("SELECT id, event, target_date, user_id FROM timers WHERE user_id IN (?, ?) ORDER BY target_date", (user_id, partner_id))
    else:
        c.execute("SELECT id, event, target_date, user_id FROM timers WHERE user_id = ? ORDER BY target_date", (user_id,))
    
    timers_list = [dict(row) for row in c.fetchall()]
    conn.close()
    return timers_list


def get_user_todos(user_id: int) -> list:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    # Знаходимо партнера
    c.execute("SELECT partner_id FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    partner_id = row[0] if row else None

    if partner_id:
        c.execute("SELECT id, title, notes, done, user_id FROM todos WHERE user_id IN (?, ?) ORDER BY id DESC", (user_id, partner_id))
    else:
        c.execute("SELECT id, title, notes, done, user_id FROM todos WHERE user_id = ? ORDER BY id DESC", (user_id,))
        
    todos_list = [dict(row) for row in c.fetchall()]
    conn.close()
    return todos_list


def get_user_notes(user_id: int) -> list:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    # Знаходимо партнера
    c.execute("SELECT partner_id FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    partner_id = row[0] if row else None

    if partner_id:
        c.execute("SELECT id, note_text as text, recipient_id, created_at, user_id FROM love_notes WHERE user_id IN (?, ?) OR recipient_id IN (?, ?) ORDER BY id DESC", (user_id, partner_id, user_id, partner_id))
    else:
        c.execute("SELECT id, note_text as text, recipient_id, created_at, user_id FROM love_notes WHERE user_id = ? OR recipient_id = ? ORDER BY id DESC", (user_id, user_id))
        
    notes_list = [dict(row) for row in c.fetchall()]
    conn.close()
    return notes_list


def find_user_by_id(user_id: int) -> dict:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT user_id, username, full_name, mood, anniversary_date, partner_id FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def find_by_username(username: str) -> tuple:
    username = username.lstrip("@").lower()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT user_id, username, full_name FROM users WHERE LOWER(username) = ?", (username,))
    row = c.fetchone()
    conn.close()
    
    if row:
        return row["user_id"], dict(row)
    return None, None


def is_blocked(blocker_id: int, target_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT 1 FROM blocked WHERE user_id = ? AND blocked_user_id = ?", (blocker_id, target_id))
    row = c.fetchone()
    conn.close()
    return bool(row)


async def show_partner_widget(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Виводить віджет зі статусом партнера"""
    user_id = update.effective_user.id
    query = update.callback_query
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Отримуємо дані користувача та партнера
    c.execute("SELECT partner_id, anniversary_date, next_visit_date FROM users WHERE user_id = ?", (user_id,))
    user_row = c.fetchone()
    
    if not user_row or not user_row['partner_id']:
        msg = "💕 Щоб бачити віджет, спочатку додайте партнера у вкладці 'Друзі'!"
        if query: await query.answer(msg, show_alert=True)
        else: await update.message.reply_text(msg)
        conn.close()
        return

    partner_id = user_row['partner_id']
    c.execute("SELECT full_name, username, mood, mood_comment, city, next_visit_date FROM users WHERE user_id = ?", (partner_id,))
    partner = c.fetchone()
    conn.close()

    if not partner:
        msg = "👤 Партнер ще не зареєструвався у боті."
        if query: await query.answer(msg, show_alert=True)
        else: await update.message.reply_text(msg)
        return

    # Розрахунок днів до зустрічі (беремо дату або у себе, або у партнера)
    visit_msg = ""
    target_date_str = partner['next_visit_date'] or user_row['next_visit_date']
    if target_date_str:
        try:
            target = datetime.strptime(target_date_str, '%Y-%m-%d')
            # Встановлюємо час на початок дня для точного розрахунку днів
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            days_left = (target - today).days
            if days_left > 0:
                visit_msg = f"\n✈️ *До зустрічі:* {days_left} днів"
            elif days_left == 0:
                visit_msg = f"\n✈️ *Зустріч СЬОГОДНІ!* 😍"
        except: pass

    # Розрахунок днів разом
    days_msg = ""
    if user_row['anniversary_date']:
        try:
            start = datetime.strptime(user_row['anniversary_date'], '%Y-%m-%d')
            days = (datetime.now() - start).days
            if days >= 0: days_msg = f"\n💕 *Ми разом:* {days} днів"
        except: pass

    # Формуємо текст віджета
    name = partner['full_name'] or f"@{partner['username']}"
    mood = partner['mood'] or "😊"
    comment = f"\n💬 _\"{partner['mood_comment']}\"_" if partner['mood_comment'] else ""
    city_info = f"\n📍 *Місто:* {partner['city']}" if partner['city'] else ""

    text = (
        f"📱 *ВІДЖЕТ ПАРТНЕРА*\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 *Партнер:* {name}\n"
        f"🎭 *Настрій:* {mood}{comment}"
        f"{city_info}"
        f"{days_msg}"
        f"{visit_msg}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🕒 _Останнє оновлення: {datetime.now().strftime('%H:%M:%S')}_"
    )
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Оновити дані", callback_data="btn_widget_refresh")],
        [InlineKeyboardButton("🚀 Відкрити Mini App", web_app=WebAppInfo(url=WEB_APP_URL))]
    ])

    if query:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
        await query.answer("Дані оновлено! ✨")
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

def main_keyboard(user_id: int = None):
    # Mini App URL береться з налаштувань (.env)
    is_https = WEB_APP_URL.startswith("https://") or "localhost" in WEB_APP_URL or "127.0.0.1" in WEB_APP_URL
    
    if is_https:
        app_button = InlineKeyboardButton("🚀 ВІДКРИТИ ДОДАТОК", web_app=WebAppInfo(url=WEB_APP_URL))
    else:
        url = f"{WEB_APP_URL}?tg_user_id={user_id}" if user_id else WEB_APP_URL
        app_button = InlineKeyboardButton("🌐 ВІДКРИТИ (БРАУЗЕР)", url=url)

    return InlineKeyboardMarkup([
        [app_button],
        [InlineKeyboardButton("📱 ВІДЖЕТ", callback_data="btn_widget_show"),
         InlineKeyboardButton("🎭 Настрій", callback_data="btn_mood")],
        [InlineKeyboardButton("📨 Надіслати", callback_data="btn_send"),
         InlineKeyboardButton("📋 Списки", callback_data="btn_todo")],
        [InlineKeyboardButton("⏳ Таймери", callback_data="btn_timer"),
         InlineKeyboardButton("💝 Love Notes", callback_data="btn_love")],
        [InlineKeyboardButton("👥 Друзі", callback_data="btn_friends"),
         InlineKeyboardButton("👤 Профіль", callback_data="btn_me")],
        [InlineKeyboardButton("📖 Команди", callback_data="btn_commands")],
    ])


def commands_keyboard():
    """Меню всіх команд (як в скріншоті BotFather)"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📨 Надіслати", callback_data="cmd_send"),
         InlineKeyboardButton("📋 Завдання", callback_data="cmd_todo")],
        [InlineKeyboardButton("⏳ Таймер", callback_data="cmd_timer"),
         InlineKeyboardButton("💝 Love Notes", callback_data="cmd_love")],
        [InlineKeyboardButton("👥 Друзі", callback_data="cmd_friends"),
         InlineKeyboardButton("👤 Профіль", callback_data="cmd_profile")],
        [InlineKeyboardButton("🔐 Блокування", callback_data="cmd_block"),
         InlineKeyboardButton("❌ Видалити дані", callback_data="cmd_delete")],
        [InlineKeyboardButton("🔙 Назад", callback_data="btn_main")],
    ])


# ─── /stats ────────────────────────────────────────────────────────────────────

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показує статистику користувача"""
    try:
        user_id = update.effective_user.id
        conn = sqlite3.connect(DB_PATH, timeout=10)
        c = conn.cursor()

        todos = c.execute("SELECT COUNT(*) FROM todos WHERE user_id = ?", (user_id,)).fetchone()[0]
        todos_done = c.execute("SELECT COUNT(*) FROM todos WHERE user_id = ? AND done = 1", (user_id,)).fetchone()[0]
        timers = c.execute("SELECT COUNT(*) FROM timers WHERE user_id = ?", (user_id,)).fetchone()[0]
        notes = c.execute("SELECT COUNT(*) FROM love_notes WHERE user_id = ?", (user_id,)).fetchone()[0]

        user_data = c.execute("SELECT coins, created_at FROM users WHERE user_id = ?", (user_id,)).fetchone()
        coins = user_data[0] if user_data and user_data[0] else 0
        created_at = user_data[1] if user_data and user_data[1] else "Невідомо"

        conn.close()

        stats_text = (
            f"📊 *Твоя статистика*\n\n"
            f"🪙 Монети: *{coins}*\n"
            f"✅ Завдань: *{todos}* (виконано: {todos_done})\n"
            f"⏰ Таймерів: *{timers}*\n"
            f"💝 Записок: *{notes}*\n"
            f"📅 Зареєстрований: {created_at[:10] if created_at != 'Невідомо' else created_at}\n\n"
            f"Продовжуй у тому ж дусі! 💪"
        )

        await update.message.reply_text(stats_text, parse_mode="Markdown")
        logger.info(f"Stats shown for user {user_id}")
    except Exception as e:
        logger.error(f"Error in stats command: {e}", exc_info=True)
        await update.message.reply_text("❌ Помилка отримання статистики. Спробуй пізніше.")

# ─── /start ────────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user = update.effective_user
        if not register(user):
            await update.message.reply_text(
                "⚠️ Встанови юзернейм у налаштуваннях Telegram, потім натисни /start."
            )
            return

        await update.message.reply_text(
            f"👋 Привіт, *{user.full_name}*!\n\n"
            f"Ти зареєстрований як *@{user.username}*.\n"
            "Обери дію нижче:",
            parse_mode="Markdown",
            reply_markup=main_keyboard(update.effective_user.id),
        )
        logger.info(f"Start command from user {user.id} (@{user.username})")
    except Exception as e:
        logger.error(f"Error in start command: {e}", exc_info=True)
        await update.message.reply_text("❌ Помилка запуску. Спробуй ще раз.")


# ─── Кнопки головного меню ─────────────────────────────────────────────────────

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "btn_me":
        await show_profile(update, context)
    elif data == "btn_help":
        await show_help(update, context)
    elif data == "btn_commands":
        await show_commands_menu(update, context)
    elif data == "btn_send":
        await query.edit_message_text(
            "📨 Введи @юзернейм отримувача або /cancel:"
        )
        return SEND_RECIPIENT
    elif data == "btn_todo":
        await show_todos(update, context)
    elif data == "btn_timer":
        await show_timer_menu(update, context)
    elif data == "btn_love":
        await show_love_notes(update, context)
    elif data == "btn_friends":
        await show_friends_menu(update, context)
    elif data == "btn_mood":
        await mood_command(update, context)
    elif data == "btn_main":
        user = update.effective_user
        await query.edit_message_text(
            f"👋 Привіт, *{user.full_name}*! Обери дію:",
            parse_mode="Markdown",
            reply_markup=main_keyboard(update.effective_user.id),
        )


async def show_commands_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показує повне меню з командами (як у BotFather скріншоті)"""
    text = (
        "📖 *ВСІ КОМАНДИ*\n\n"
        "*📨 ПОВІДОМЛЕННЯ*\n"
        "/send — надіслати\n"
        "/block @username — заблокувати\n"
        "/unblock @username — розблокувати\n"
        "/blocklist — список заблокованих\n\n"
        "*📋 ЗАВДАННЯ*\n"
        "/todo — мої завдання\n"
        "/todoadd — додати завдання\n\n"
        "*⏳ ТАЙМЕР (до 5)*\n"
        "/timer — менеджер таймерів\n"
        "/timeradd — додати новий\n\n"
        "*💝 LOVE NOTES*\n"
        "/lovenote — написати записку\n"
        "/mynotes — мої записки\n\n"
        "*👥 ДРУЗІ & СИНХРОНІЗАЦІЯ*\n"
        "/addfriend <ID> — додати друга за ID\n"
        "/friends — мої друзі\n"
        "/sharedata — синхронізувати дані\n\n"
        "*👤 ПРОФІЛЬ*\n"
        "/me — мій профіль\n"
        "/help — допомога\n"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="btn_main")]])
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)


async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    register(user)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM blocked WHERE user_id = ?", (user.id,))
    bl_count = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM todos WHERE user_id = ?", (user.id,))
    todo_count = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM love_notes WHERE user_id = ?", (user.id,))
    notes_count = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    conn.close()

    is_admin = user.id in ADMIN_IDS

    text = (
        f"👤 *Твій профіль*\n\n"
        f"Ім'я: {user.full_name}\n"
        f"Юзернейм: @{user.username}\n"
        f"ID: `{user.id}`\n"
        f"Заблоковано: {bl_count} користувачів\n"
        f"📋 Завдань: {todo_count}\n"
        f"💝 Love Notes: {notes_count}\n"
        f"{'👑 Адміністратор' if is_admin else ''}\n\n"
        f"Всього в боті: *{total_users}* користувачів"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="btn_main")]])
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "📖 *ДОПОМОГА*\n\n"
        "*📨 ПОВІДОМЛЕННЯ*\n"
        "Надсилай повідомлення, фото, відео друзям\n\n"
        "*📋 ЗАВДАННЯ (СПИСОК)*\n"
        "Веди список спільних справ з дівчиною\n\n"
        "*⏳ ТАЙМЕР (ДО 5)*\n"
        "Відраховуй дні до зустрічи, дня народження тощо\n\n"
        "*💝 LOVE NOTES*\n"
        "Пиши романтичні записки за адресою\n\n"
        "*👥 ДРУЗІ & СИНХРОНІЗАЦІЯ*\n"
        "Додавай друзів за ID і синхронізуй дані\n\n"
        "_Натисни 📖 Команди у меню для повного списку!_"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="btn_main")]])
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)


async def todo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await show_todos(update, context)


async def love_note_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await show_love_notes(update, context)


# ─── /send (з оригіналу) ─────────────────────────────────────────────────────────

async def send_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    if not register(user):
        await update.message.reply_text("⚠️ Встанови юзернейм та спробуй знову.")
        return ConversationHandler.END

    await update.message.reply_text("📨 Введи @юзернейм отримувача або /cancel:")
    return SEND_RECIPIENT


async def send_get_recipient(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    sender = update.effective_user
    username = update.message.text.strip().lstrip("@").lower()

    if username == (sender.username or "").lower():
        await update.message.reply_text("❌ Не можна надіслати собі. Введи інший @username:")
        return SEND_RECIPIENT

    recipient_id, recipient_data = find_by_username(username)
    if not recipient_id:
        await update.message.reply_text(
            f"❌ @{username} не знайдено. Переконайся що людина запустила бота.\nСпробуй ще раз або /cancel:"
        )
        return SEND_RECIPIENT

    if is_blocked(recipient_id, sender.id):
        await update.message.reply_text("🚫 Цей користувач заблокував тебе.")
        return ConversationHandler.END

    context.user_data["r_id"] = recipient_id
    context.user_data["r_username"] = recipient_data["username"]

    await update.message.reply_text(
        f"✅ Отримувач: *@{recipient_data['username']}* ({recipient_data['full_name']})\n\n"
        "Напиши повідомлення (текст, фото, відео, стікер...):",
        parse_mode="Markdown",
    )
    return SEND_MESSAGE


async def deliver_media(bot, chat_id: int, msg, header: str, reply_kb):
    """Надіслати будь-який тип медіа з заголовком."""
    if msg.text:
        await bot.send_message(chat_id, header + msg.text,
                               parse_mode="Markdown", reply_markup=reply_kb)
    elif msg.photo:
        cap = (header + msg.caption) if msg.caption else header.strip()
        await bot.send_photo(chat_id, msg.photo[-1].file_id,
                             caption=cap, parse_mode="Markdown", reply_markup=reply_kb)
    elif msg.video:
        cap = (header + msg.caption) if msg.caption else header.strip()
        await bot.send_video(chat_id, msg.video.file_id,
                             caption=cap, parse_mode="Markdown", reply_markup=reply_kb)
    elif msg.sticker:
        await bot.send_message(chat_id, header.strip(),
                               parse_mode="Markdown", reply_markup=reply_kb)
        await bot.send_sticker(chat_id, msg.sticker.file_id)
    elif msg.voice:
        await bot.send_message(chat_id, header.strip(),
                               parse_mode="Markdown", reply_markup=reply_kb)
        await bot.send_voice(chat_id, msg.voice.file_id)
    elif msg.audio:
        cap = (header + msg.caption) if msg.caption else header.strip()
        await bot.send_audio(chat_id, msg.audio.file_id,
                             caption=cap, parse_mode="Markdown", reply_markup=reply_kb)
    elif msg.document:
        cap = (header + msg.caption) if msg.caption else header.strip()
        await bot.send_document(chat_id, msg.document.file_id,
                                caption=cap, parse_mode="Markdown", reply_markup=reply_kb)
    elif msg.video_note:
        await bot.send_message(chat_id, header.strip(),
                               parse_mode="Markdown", reply_markup=reply_kb)
        await bot.send_video_note(chat_id, msg.video_note.file_id)
    else:
        return False
    return True


async def send_deliver(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    sender = update.effective_user
    recipient_id = context.user_data.get("r_id")
    recipient_username = context.user_data.get("r_username")

    if not recipient_id:
        await update.message.reply_text("❌ Помилка. Почни знову: /send")
        return ConversationHandler.END

    sender_tag = f"@{sender.username}" if sender.username else sender.full_name
    header = f"📩 *Нове повідомлення від {sender_tag}:*\n\n"
    reply_kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("↩️ Відповісти",
                             callback_data=f"reply:{sender.id}:{sender_tag}")
    ]])

    try:
        ok = await deliver_media(context.bot, recipient_id, update.message, header, reply_kb)
        if not ok:
            await update.message.reply_text("❌ Цей тип медіа не підтримується.")
            return ConversationHandler.END

        await update.message.reply_text(
            f"✅ Повідомлення надіслано *@{recipient_username}*!",
            parse_mode="Markdown",
        )
        logger.info("MSG: %s → @%s", sender_tag, recipient_username)
    except Exception as e:
        logger.error("Send error: %s", e)
        await update.message.reply_text("❌ Не вдалося надіслати. Можливо отримувач заблокував бота.")

    context.user_data.clear()
    return ConversationHandler.END


async def send_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("❌ Скасовано.", reply_markup=main_keyboard(update.effective_user.id))
    return ConversationHandler.END


async def reply_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    parts = query.data.split(":", 2)
    from_id = int(parts[1])
    from_label = parts[2]

    user = update.effective_user
    register(user)

    if is_blocked(from_id, user.id):
        await query.answer("🚫 Цей користувач заблокував тебе.", show_alert=True)
        return ConversationHandler.END

    pending_replies[user.id] = {"from_id": from_id, "from_label": from_label}

    await context.bot.send_message(
        user.id,
        f"↩️ Відповідаєш *{from_label}*.\nНапиши повідомлення або /cancel:",
        parse_mode="Markdown",
    )
    return REPLY_MESSAGE


async def reply_deliver(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    reply_data = pending_replies.pop(user.id, None)

    if not reply_data:
        await update.message.reply_text("❌ Помилка. Спробуй знову.")
        return ConversationHandler.END

    to_id = reply_data["from_id"]
    sender_tag = f"@{user.username}" if user.username else user.full_name
    header = f"↩️ *Відповідь від {sender_tag}:*\n\n"
    reply_kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("↩️ Відповісти",
                             callback_data=f"reply:{user.id}:{sender_tag}")
    ]])

    try:
        ok = await deliver_media(context.bot, to_id, update.message, header, reply_kb)
        if not ok:
            await update.message.reply_text("❌ Цей тип медіа не підтримується.")
            return ConversationHandler.END
        await update.message.reply_text("✅ Відповідь надіслано!")
    except Exception as e:
        logger.error("Reply error: %s", e)
        await update.message.reply_text("❌ Не вдалося надіслати відповідь.")

    return ConversationHandler.END


async def reply_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    pending_replies.pop(update.effective_user.id, None)
    await update.message.reply_text("❌ Відповідь скасовано.")
    return ConversationHandler.END


# ─── БЛОКУВАННЯ ────────────────────────────────────────────────────────────────

async def block_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    register(user)
    if not context.args:
        await update.message.reply_text("Використання: /block @username")
        return
    target_id, target_data = find_by_username(context.args[0])
    if not target_id:
        await update.message.reply_text("❌ Користувача не знайдено.")
        return
    if target_id == user.id:
        await update.message.reply_text("❌ Не можна заблокувати себе.")
        return
    save_blocked_to_db(user.id, target_id)  # ← ЗБЕРІГАЄМО В БД
    await update.message.reply_text(f"🚫 @{target_data['username']} заблокований.")


async def unblock_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    register(user)
    if not context.args:
        await update.message.reply_text("Використання: /unblock @username")
        return
    target_id, target_data = find_by_username(context.args[0])
    if not target_id:
        await update.message.reply_text("❌ Користувача не знайдено.")
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM blocked WHERE user_id = ? AND blocked_user_id = ?", (user.id, target_id))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"✅ @{target_data['username']} розблокований.")


async def block_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показує список заблокованих користувачів"""
    user = update.effective_user
    register(user)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT b.blocked_user_id, u.username 
        FROM blocked b 
        LEFT JOIN users u ON b.blocked_user_id = u.user_id 
        WHERE b.user_id = ?
    ''', (user.id,))
    bl_rows = c.fetchall()
    conn.close()

    if not bl_rows:
        await update.message.reply_text("✅ Список заблокованих порожній.")
        return
        
    lines = []
    for uid, username in bl_rows:
        lines.append(f"• @{username}" if username else f"• ID:{uid}")
        
    await update.message.reply_text(
        "🚫 *Заблоковані користувачі:*\n" + "\n".join(lines),
        parse_mode="Markdown",
    )


# ════════════════════════════════════════════════════════════════════════════════
# ═══════════════════ 📋 СПИСОК ЗАВДАНЬ ДЛЯ ДВОХ 📋 ═════════════════════════════
# ════════════════════════════════════════════════════════════════════════════════

async def show_todos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    register(user)
    
    # ЧИТАЄМО З БАЗИ ДАНИХ ПРЯМО ЗАРАЗ
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT id, title, notes, done FROM todos WHERE user_id = ? ORDER BY id DESC", (user.id,))
    user_todos = [dict(row) for row in c.fetchall()]
    conn.close()

    if not user_todos:
        text = "📋 *Список завдань*\n\nУ тебе ще нічого немає.\nНадай /todoadd щоб додати!"
    else:
        lines = []
        for i, todo in enumerate(user_todos, 1):
            status = "✅" if todo.get("done") else "⬜"
            lines.append(f"{status} {i}. {todo['title']}")
            if todo.get("notes"):
                lines.append(f"   📝 {todo['notes']}")
        text = "📋 *Твої завдання:*\n\n" + "\n".join(lines)

    buttons = [
        [InlineKeyboardButton("➕ Додати", callback_data="todo_add")],
        [InlineKeyboardButton("✅ Позначити виконаним", callback_data="todo_toggle_menu")],
        [InlineKeyboardButton("❌ Видалити", callback_data="todo_delete")],
        [InlineKeyboardButton("🔙 Назад", callback_data="btn_main")],
    ]
    kb = InlineKeyboardMarkup(buttons)

    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)


async def todo_add_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("📋 Введи назву завдання (або /cancel):")
    else:
        await update.message.reply_text("📋 Введи назву завдання (або /cancel):")
    return TODO_ADD_TITLE


async def todo_add_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    title = update.message.text.strip()
    if len(title) > 100:
        await update.message.reply_text("❌ Занадто довго. Максимум 100 символів.")
        return TODO_ADD_TITLE

    context.user_data["todo_title"] = title
    await update.message.reply_text(
        "📝 Додай нотатку (опціонально, або просто напиши /skip або /cancel):"
    )
    return TODO_ADD_NOTES


async def todo_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    register(user)

    title = context.user_data.get("todo_title", "")
    notes = ""

    if update.message.text.strip().lower() != "/skip":
        notes = update.message.text.strip()[:200]

    save_todo_to_db(user.id, title, notes)  # ← ЗБЕРІГАЄМО В БД
    context.user_data.clear()

    await update.message.reply_text(
        f"✅ Завдання додано!\n\n*{title}*\n{notes}",
        parse_mode="Markdown",
    )
    
    # Показуємо список знову
    await show_todos(update, context)
    return ConversationHandler.END


async def todo_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("❌ Скасовано.")
    return ConversationHandler.END


# ════════════════════════════════════════════════════════════════════════════════
# ═══════════════════ ⏳ ТАЙМЕР ЗВОРОТНОГО ВІДЛІКУ ⏳ ════════════════════════════
# ════════════════════════════════════════════════════════════════════════════════

async def show_timer_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    register(user)
    
    # ЧИТАЄМО З БАЗИ ДАНИХ ПРЯМО ЗАРАЗ
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT id, event, target_date FROM timers WHERE user_id = ? ORDER BY target_date", (user.id,))
    user_timers = [dict(row) for row in c.fetchall()]
    conn.close()

    if not user_timers:
        text = "⏳ *Таймери*\n\nУ тебе ще немає активних таймерів.\nМаксимум 5 таймерів!"
    else:
        lines = []
        for i, timer in enumerate(user_timers, 1):
            target_date = datetime.strptime(timer["target_date"], "%Y-%m-%d")
            now = datetime.now()
            
            # Обнуляємо години для точного розрахунку днів як на сайті
            target_date_zero = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            now_zero = now.replace(hour=0, minute=0, second=0, microsecond=0)
            delta = target_date_zero - now_zero

            if delta.days >= 0:
                lines.append(f"{i}. ⏳ *{timer['event']}* — {delta.days} днів")
            else:
                lines.append(f"{i}. 🎉 *{timer['event']}* — ГОТОВО!")

        text = f"⏳ *Твої таймери ({len(user_timers)}/5):*\n\n" + "\n".join(lines)

    buttons = [
        [InlineKeyboardButton("➕ Додати", callback_data="timer_add")] if len(user_timers) < 5 else [],
        [InlineKeyboardButton("📝 Деталі", callback_data="timer_details"),
         InlineKeyboardButton("🗑️ Видалити", callback_data="timer_delete")],
        [InlineKeyboardButton("🔙 Назад", callback_data="btn_main")],
    ]
    kb = InlineKeyboardMarkup([b for b in buttons if b])

    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)


async def timer_add_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    if len(get_user_timers(user.id)) >= 5:
        await update.callback_query.answer("❌ Максимум 5 таймерів!", show_alert=True)
        return ConversationHandler.END
    await update.callback_query.edit_message_text(
        "📅 Введи дату (формат: РРРР-ММ-ДД, наприклад: 2025-04-15) або /cancel:"
    )
    return TIMER_SET_DATE


async def timer_set_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    register(user)
    date_str = update.message.text.strip()

    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d")
        if target_date < datetime.now():
            await update.message.reply_text("❌ Дата має бути в майбутньому!")
            return TIMER_SET_DATE

        await update.message.reply_text(
            "✍️ Як назвати цю подію? (наприклад: Зустріч, День народження)"
        )
        context.user_data["timer_date"] = date_str
        return TIMER_SET_EVENT

    except ValueError:
        await update.message.reply_text("❌ Неправильний формат! Спробуй: 2025-04-15 або /cancel")
        return TIMER_SET_DATE


async def timer_set_event(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    event_name = update.message.text.strip()[:50]
    date_str = context.user_data.get("timer_date")

    save_timer_to_db(user.id, event_name, date_str)  # ← ЗБЕРІГАЄМО В БД
    context.user_data.clear()

    await update.message.reply_text(
        f"✅ Таймер додано!\n⏳ До {event_name}: {date_str}",
        reply_markup=main_keyboard(update.effective_user.id),
    )
    return ConversationHandler.END


# ════════════════════════════════════════════════════════════════════════════════
# ═══════════════════ 💝 LOVE NOTES 💝 ═════════════════════════════════════════
# ════════════════════════════════════════════════════════════════════════════════

async def show_love_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    register(user)

    # ЧИТАЄМО З БАЗИ ДАНИХ ПРЯМО ЗАРАЗ
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(
        "SELECT id, note_text, recipient_id FROM love_notes WHERE user_id = ? ORDER BY id DESC",
        (user.id,)
    )
    user_notes = [dict(row) for row in c.fetchall()]
    conn.close()

    if not user_notes:
        text = "💝 *Love Notes*\n\nУ тебе ще нічого немає.\nНапиши першу записку! 💕"
    else:
        lines = []
        for i, note in enumerate(user_notes, 1):
            recipient_name = "Приватна"
            if note.get("recipient_id"):
                # Шукаємо ім'я отримувача в базі
                conn = sqlite3.connect(DB_PATH)
                c_sub = conn.cursor()
                c_sub.execute("SELECT username FROM users WHERE user_id = ?", (note["recipient_id"],))
                r_row = c_sub.fetchone()
                if r_row:
                    recipient_name = f"@{r_row[0]}"
                conn.close()

            short_note = note["note_text"][:40] + "..." if len(note["note_text"]) > 40 else note["note_text"]
            lines.append(f"{i}. [{recipient_name}] {short_note}")
        text = "💝 *Твої записки:*\n\n" + "\n".join(lines) + f"\n\n_Всього: {len(user_notes)}_"
    buttons = [
        [InlineKeyboardButton("✍️ Написати", callback_data="love_write")],
        [InlineKeyboardButton("🔙 Назад", callback_data="btn_main")],
    ]
    kb = InlineKeyboardMarkup(buttons)

    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)


async def love_write_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()

    user = update.effective_user
    user_friends = get_user_friends(user.id)

    if user_friends:
        buttons = []
        buttons.append([InlineKeyboardButton("🔒 Приватна записка", callback_data="love_private")])
        for friend_id in list(user_friends)[:5]:
            f_data = find_user_by_id(friend_id)
            if f_data:
                buttons.append([InlineKeyboardButton(f"💝 @{f_data['username']}",
                                                     callback_data=f"love_for:{friend_id}")])
        buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="btn_love")])
        kb = InlineKeyboardMarkup(buttons)
        text = "💝 Кому ця записка?"
        if query:
            await query.edit_message_text(text, reply_markup=kb)
        else:
            await update.message.reply_text(text, reply_markup=kb)
        return LOVE_NOTE_RECIPIENT
    else:
        text = "💝 Напиши записку (максимум 500 символів) або /cancel:"
        if query:
            await query.edit_message_text(text)
        else:
            await update.message.reply_text(text)
        context.user_data["love_recipient_id"] = None
        return LOVE_NOTE_TEXT


async def love_note_recipient_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "love_private":
        context.user_data["love_recipient_id"] = None
    else:
        recipient_id = int(data.split(":")[1])
        context.user_data["love_recipient_id"] = recipient_id
    
    await query.edit_message_text(
        "💝 Напиши записку (максимум 500 символів) або /cancel:"
    )
    return LOVE_NOTE_TEXT


async def love_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    register(user)
    
    note_text = update.message.text.strip()
    if len(note_text) > 500:
        await update.message.reply_text("❌ Занадто довго. Максимум 500 символів.")
        return LOVE_NOTE_TEXT

    recipient_id = context.user_data.get("love_recipient_id")
    
    new_note = {
        "text": note_text,
        "recipient_id": recipient_id,
        "created": str(datetime.now()),
    }
    
    # love_notes[user.id].append(new_note)
    save_love_note_to_db(user.id, note_text, recipient_id)  # ← ЗБЕРІГАЄМО В БД
    
    recipient_name = "Приватна"
    if recipient_id:
        r_data = find_user_by_id(recipient_id)
        if r_data:
            recipient_name = f"@{r_data['username']}"

    await update.message.reply_text(
        f"💕 Записка збережена ({recipient_name})!\n\n_{note_text}_",
        parse_mode="Markdown",
        reply_markup=main_keyboard(update.effective_user.id),
    )
    context.user_data.clear()
    return ConversationHandler.END


async def love_read(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    user_notes = get_user_notes(user.id)

    if not user_notes:
        await query.answer("📖 Записок немає!", show_alert=True)
        return

    context.user_data["note_index"] = 0
    await show_single_note(query, user, context)


async def show_single_note(query, user, context):
    user_notes = get_user_notes(user.id)
    index = context.user_data.get("note_index", 0)

    if index >= len(user_notes):
        index = len(user_notes) - 1
        context.user_data["note_index"] = index

    if index < 0 or not user_notes:
        return

    note = user_notes[index]
    recipient_name = "Приватна"
    if note.get("recipient_id"):
        r_data = find_user_by_id(note["recipient_id"])
        if r_data:
            recipient_name = f"@{r_data['username']}"
    
    text = f"💝 *Записка {index + 1} з {len(user_notes)}* [{recipient_name}]\n\n{note['text']}"

    buttons = []
    nav_buttons = []
    if index > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️", callback_data="love_prev"))
    if index < len(user_notes) - 1:
        nav_buttons.append(InlineKeyboardButton("➡️", callback_data="love_next"))

    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="btn_love")])
    kb = InlineKeyboardMarkup(buttons)

    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)


async def love_note_nav(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    direction = query.data
    if direction == "love_next":
        context.user_data["note_index"] = context.user_data.get("note_index", 0) + 1
    elif direction == "love_prev":
        context.user_data["note_index"] = context.user_data.get("note_index", 0) - 1

    await show_single_note(query, user, context)


async def show_friends_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    register(user)
    user_friends = get_user_friends(user.id)
    me = find_user_by_id(user.id)
    partner_id = me.get('partner_id')

    text = "👥 *МЕНЮ КОНТАКТІВ*\n\n"
    
    if partner_id:
        p_data = find_user_by_id(partner_id)
        text += f"💖 *Твоя пара:* {p_data['full_name']} (@{p_data['username']})\n\n"
    else:
        text += "💖 *Пара:* Не обрано (спільний простір вимкнено)\n\n"

    if not user_friends:
        text += "👥 *Друзі:* Список порожній."
    else:
        lines = []
        for friend_id in user_friends:
            if friend_id == partner_id: continue
            f_data = find_user_by_id(friend_id)
            if f_data:
                lines.append(f"• @{f_data['username']} (ID: {friend_id})")
        text += "👥 *Твої друзі:* \n" + ("\n".join(lines) if lines else "Немає інших друзів.")

    buttons = [
        [InlineKeyboardButton("💖 ОБРАТИ ПАРУ", callback_data="partner_add_start")],
        [InlineKeyboardButton("👥 ДОДАТИ ДРУГА", callback_data="friend_add_start")],
        [InlineKeyboardButton("🔄 Синхронізація", callback_data="friend_sync")],
        [InlineKeyboardButton("🔙 Назад", callback_data="btn_main")],
    ]
    kb = InlineKeyboardMarkup(buttons)

    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)

async def partner_add_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "💖 *СТАТИ ПАРОЮ*\n\nВведи ID своєї половинки. \n"
        "Після підтвердження ваші таймери, завдання та записки стануть СПІЛЬНИМИ!",
        parse_mode="Markdown"
    )
    return ADD_PARTNER_ID 

async def friend_add_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "👥 *ДОДАТИ ДРУГА*\n\nВведи ID друга. \n"
        "Ви зможете бачити настрій одне одного, але ваші приватні дані залишаться особистими.",
        parse_mode="Markdown"
    )
    return ADD_FRIEND_ID


async def send_partner_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Відправляє запит стати парою"""
    user = update.effective_user
    register(user)
    try:
        target_id = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ ID має бути числом!")
        return ADD_FRIEND_ID

    if target_id == user.id:
        await update.message.reply_text("❌ Не можна стати парою з самим собою!")
        return ADD_FRIEND_ID

    target_data = find_user_by_id(target_id)
    if not target_data:
        await update.message.reply_text("❌ Користувач не знайдений або не запустив бота.")
        return ADD_FRIEND_ID

    # Перевірка чи вже є партнер
    me = find_user_by_id(user.id)
    if me.get('partner_id'):
        await update.message.reply_text("❌ У тебе вже є партнер! Спочатку розірви старі стосунки.")
        return ConversationHandler.END

    # Відправка запиту
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Прийняти", callback_data=f"couple_accept:{user.id}"),
         InlineKeyboardButton("❌ Відхилити", callback_data="couple_decline")]
    ])

    try:
        await context.bot.send_message(
            target_id,
            f"💖 Користувач *{user.full_name}* (@{user.username}) хоче стати твоєю парою!\n\n"
            "Якщо ви приймете запит, ваші списки завдань, таймери та записки стануть спільними.",
            parse_mode="Markdown",
            reply_markup=kb
        )
        await update.message.reply_text(f"🚀 Запит надіслано @{target_data['username']}! Чекаємо на відповідь...")
    except Exception:
        await update.message.reply_text("❌ Не вдалося надіслати запит. Можливо, користувач заблокував бота.")

    context.user_data.clear()
    return ConversationHandler.END

async def accept_partner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    partner_id = int(query.data.split(":")[1])
    user = update.effective_user

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Оновлюємо обох
    c.execute("UPDATE users SET partner_id = ? WHERE user_id = ?", (partner_id, user.id))
    c.execute("UPDATE users SET partner_id = ? WHERE user_id = ?", (user.id, partner_id))
    # Також додаємо в друзі для сумісності
    c.execute("INSERT OR IGNORE INTO friends (user_id, friend_id) VALUES (?, ?)", (user.id, partner_id))
    c.execute("INSERT OR IGNORE INTO friends (user_id, friend_id) VALUES (?, ?)", (partner_id, user.id))
    conn.commit()
    conn.close()

    partner_data = find_user_by_id(partner_id)
    await query.edit_message_text(f"🎊 Вітаємо! Тепер ви пара з *{partner_data['full_name']}*! Спільний простір активовано.", parse_mode="Markdown")

    try:
        await context.bot.send_message(partner_id, f"💖 *{user.full_name}* прийняв(ла) твій запит! Тепер ви пара.")
    except: pass

async def friend_add_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Додає просто в друзі (без спільного простору)"""
    user = update.effective_user
    try:
        friend_id = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ ID має бути числом!")
        return ADD_FRIEND_ID

    if friend_id == user.id:
        await update.message.reply_text("❌ Не можна додати себе!")
        return ADD_FRIEND_ID

    friend_data = find_user_by_id(friend_id)
    if not friend_data:
        await update.message.reply_text("❌ Користувач не знайдений.")
        return ADD_FRIEND_ID

    save_friend_to_db(user.id, friend_id)
    save_friend_to_db(friend_id, user.id)

    await update.message.reply_text(
        f"✅ @{friend_data['username']} доданий(а) у друзі!",
        reply_markup=main_keyboard(user.id)
    )
    
    try:
        await context.bot.send_message(friend_id, f"👥 @{user.username} додав тебе у друзі!")
    except: pass
    
    context.user_data.clear()
    return ConversationHandler.END
async def friend_sync(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Синхронізація даних з парою або друзями"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    me = find_user_by_id(user.id)
    partner_id = me.get('partner_id')
    
    if not partner_id:
        await query.edit_message_text(
            "⚠️ У тебе ще не обрано пару для синхронізації.\n"
            "Обери '💖 ОБРАТИ ПАРУ' в меню контактів.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="btn_friends")]])
        )
        return

    # Якщо пара є, показуємо статус спільного простору
    p_data = find_user_by_id(partner_id)
    user_todos = get_user_todos(user.id)
    user_timers = get_user_timers(user.id)

    text = (
        f"🔄 *СИНХРОНІЗАЦІЯ ПАРИ*\n\n"
        f"Ти в парі з: *{p_data['full_name']}*\n"
        f"Статус: Спільний простір АКТИВНО ✅\n\n"
        f"📋 Спільних завдань: {len(user_todos)}\n"
        f"⏳ Спільних таймерів: {len(user_timers)}\n\n"
        f"Ваші завдання, таймери та записки автоматично об'єднані."
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="btn_friends")]])
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)


async def sync_todos_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Поділитись всіма завданнями з друзями"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    user_friends = get_user_friends(user.id)
    user_todos = get_user_todos(user.id)

    if not user_todos:
        await query.answer("❌ У тебе немає завдань для синхронізації!", show_alert=True)
        return

    user_data = find_user_by_id(user.id)
    # Надсилаємо завдання кожному другу
    success_count = 0
    for friend_id in user_friends:
        try:
            todo_list = "\n".join([f"• {t['title']}" for t in user_todos])
            await context.bot.send_message(
                friend_id,
                f"📋 @{user_data['username']} поділився завданнями:\n\n{todo_list}",
                reply_markup=main_keyboard(update.effective_user.id),
            )
            success_count += 1
        except Exception:
            pass

    await query.edit_message_text(
        f"✅ Завдання синхронізовано з {success_count} друзями!",
        reply_markup=main_keyboard(update.effective_user.id),
    )


async def sync_timers_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Поділитись всіма таймерами з друзями"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    user_friends = get_user_friends(user.id)
    user_timers = get_user_timers(user.id)

    if not user_timers:
        await query.answer("❌ У тебе немає таймерів для синхронізації!", show_alert=True)
        return

    user_data = find_user_by_id(user.id)
    # Надсилаємо таймери кожному другу
    success_count = 0
    for friend_id in user_friends:
        try:
            timer_list = "\n".join([
                f"⏳ {t['event']} — {t['target_date']}"
                for t in user_timers
            ])
            await context.bot.send_message(
                friend_id,
                f"⏳ @{user_data['username']} поділився таймерами:\n\n{timer_list}",
                reply_markup=main_keyboard(update.effective_user.id),
            )
            success_count += 1
        except Exception:
            pass

    await query.edit_message_text(
        f"✅ Таймери синхронізовано з {success_count} друзями!",
        reply_markup=main_keyboard(update.effective_user.id),
    )


# ════════════════════════════════════════════════════════════════════════════════
# ═══════════════════ 🤖 ВСТАНОВЛЕННЯ КОМАНД В МЕНЮ ════════════════════════════
# ════════════════════════════════════════════════════════════════════════════════

async def set_bot_commands(app: Application) -> None:
    """Встановлює команди в меню BotFather (як на фото)"""
    commands = [
        BotCommand("start", "🚀 Запустити бота"),
        BotCommand("stats", "📊 Моя статистика"),
        BotCommand("send", "📨 Надіслати повідомлення"),
        BotCommand("todo", "📋 Список завдань"),
        BotCommand("todoadd", "➕ Додати завдання"),
        BotCommand("timer", "⏳ Управління таймерами"),
        BotCommand("timeradd", "➕ Додати таймер"),
        BotCommand("lovenote", "💝 Написати Love Note"),
        BotCommand("mynotes", "📖 Мої записки"),
        BotCommand("addfriend", "👥 Додати друга за ID"),
        BotCommand("friends", "👥 Мої друзі"),
        BotCommand("daily", "❓ Питання дня"),
        BotCommand("block", "🚫 Заблокувати"),
        BotCommand("unblock", "✅ Розблокувати"),
        BotCommand("blocklist", "📋 Заблоковані"),
        BotCommand("mood", "🎭 Встановити настрій"),
        BotCommand("widget", "📱 Віджет партнера"),
        BotCommand("help", "❓ Допомога"),
        BotCommand("me", "👤 Мій профіль"),
    ]
    
    await app.bot.set_my_commands(commands)
    logger.info("✅ Команди встановлено в меню BotFather!")


# ─── ПОЗНАЧЕННЯ ЗАВДАНЬ (ВИКОНАНО/НЕ ВИКОНАНО) ──────────────────────────────────

async def todo_toggle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT id, title, done FROM todos WHERE user_id = ? ORDER BY id DESC", (user.id,))
    user_todos = [dict(row) for row in c.fetchall()]
    conn.close()

    if not user_todos:
        await query.edit_message_text(
            "❌ У тебе немає завдань.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="btn_todo")]]),
        )
        return

    buttons = []
    for todo in user_todos:
        icon = "✅" if todo["done"] else "⬜"
        action = "uncheck" if todo["done"] else "check"
        buttons.append([InlineKeyboardButton(f"{icon} {todo['title']}", callback_data=f"todo_tgl:{todo['id']}:{action}")])
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="btn_todo")])

    await query.edit_message_text("Натисни на завдання щоб змінити статус:", reply_markup=InlineKeyboardMarkup(buttons))


async def todo_toggle_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    parts = query.data.split(":")
    todo_id = int(parts[1])
    action = parts[2]
    user = update.effective_user

    new_done = 1 if action == "check" else 0
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE todos SET done = ? WHERE id = ? AND user_id = ?", (new_done, todo_id, user.id))
    conn.commit()
    conn.close()

    status = "виконано ✅" if new_done else "не виконано ⬜"
    await query.answer(f"Статус змінено: {status}")
    await todo_toggle_menu(update, context)


# ─── ВИДАЛЕННЯ ЗАВДАНЬ (ВИБІРКОВО) ─────────────────────────────────────────────

async def todo_delete_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT id, title FROM todos WHERE user_id = ? ORDER BY id DESC", (user.id,))
    user_todos = [dict(row) for row in c.fetchall()]
    conn.close()

    if not user_todos:
        await query.edit_message_text("❌ У тебе немає завдань для видалення.", 
                                     reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="btn_todo")]]))
        return

    buttons = []
    for todo in user_todos:
        buttons.append([InlineKeyboardButton(f"❌ {todo['title']}", callback_data=f"todo_del:{todo['id']}")])
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="btn_todo")])

    await query.edit_message_text("🗑️ Обери завдання, яке хочеш видалити:", reply_markup=InlineKeyboardMarkup(buttons))


async def todo_delete_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    todo_id = int(query.data.split(":")[1])
    user = update.effective_user

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM todos WHERE id = ? AND user_id = ?", (todo_id, user.id))
    conn.commit()
    conn.close()

    await query.answer("✅ Завдання видалено!")
    await todo_delete_menu(update, context)


# ─── ВИДАЛЕННЯ ТАЙМЕРІВ (ВИБІРКОВО) ───────────────────────────────────────────

async def timer_delete_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT id, event FROM timers WHERE user_id = ? ORDER BY id DESC", (user.id,))
    user_timers = [dict(row) for row in c.fetchall()]
    conn.close()

    if not user_timers:
        await query.edit_message_text("❌ У тебе немає таймерів для видалення.", 
                                     reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="btn_timer")]]))
        return

    buttons = []
    for timer in user_timers:
        buttons.append([InlineKeyboardButton(f"❌ {timer['event']}", callback_data=f"timer_del:{timer['id']}")])
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="btn_timer")])

    await query.edit_message_text("🗑️ Обери таймер для видалення:", reply_markup=InlineKeyboardMarkup(buttons))


async def timer_delete_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    timer_id = int(query.data.split(":")[1])
    user = update.effective_user

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM timers WHERE id = ? AND user_id = ?", (timer_id, user.id))
    conn.commit()
    conn.close()

    await query.answer("✅ Таймер видалено!")
    await timer_delete_menu(update, context)


async def daily_question_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Відправляє поточне питання дня"""
    user = update.effective_user
    register(user)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    day_offset = (datetime.now() - datetime(2025, 1, 1)).days
    c.execute("SELECT * FROM daily_questions ORDER BY id")
    questions = c.fetchall()
    
    if not questions:
        default_q = [
            "Яка твоя найулюбленіша спільна поїздка?",
            "Що в мені викликає у тебе посмішку найчастіше?",
            "Яку нову навичку ми могли б вивчити разом?",
            "Якби ми могли переїхати в будь-яку точку світу, куди б ми поїхали?",
            "Яка твоя улюблена страва, яку ми готували разом?",
            "Який фільм ми маємо обов'язково переглянути наступним?",
            "Що було твоїм першим враженням про мене?"
        ]
        for q in default_q:
            c.execute("INSERT INTO daily_questions (question) VALUES (?)", (q,))
        conn.commit()
        c.execute("SELECT * FROM daily_questions ORDER BY id")
        questions = c.fetchall()
        
    q = questions[day_offset % len(questions)]
    conn.close()
    
    text = f"❓ *ПИТАННЯ ДНЯ*\n\n{q['question']}\n\nВідповідай у Mini App!"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Відповісти", web_app=WebAppInfo(url=WEB_APP_URL))]])
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)

# ─── НАСТРІЙ (/mood) ────────────────────────────────────────────────────────────

MOODS = ["😊", "😍", "😎", "🥰", "😴", "😔", "😤", "🤒", "🎉", "💪"]

async def mood_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Дозволяє встановити настрій через кнопки"""
    user = update.effective_user
    register(user)
    buttons = [
        [InlineKeyboardButton(m, callback_data=f"mood_set:{m}") for m in MOODS[:5]],
        [InlineKeyboardButton(m, callback_data=f"mood_set:{m}") for m in MOODS[5:]],
    ]
    kb = InlineKeyboardMarkup(buttons)
    text = "🎭 *Який у тебе зараз настрій?*\nОбери emoji:"
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)


async def mood_set_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    mood = query.data.split(":")[1]
    user = update.effective_user

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET mood = ? WHERE user_id = ?", (mood, user.id))
    conn.commit()
    conn.close()

    # Повідомляємо партнера про зміну настрою
    me = find_user_by_id(user.id)
    partner_id = me.get("partner_id") if me else None
    if partner_id:
        try:
            await context.bot.send_message(
                partner_id,
                f"🎭 *{user.full_name}* змінив(ла) настрій на {mood}",
                parse_mode="Markdown",
            )
        except Exception:
            pass

    await query.answer(f"Настрій встановлено: {mood}", show_alert=False)
    await query.edit_message_text(
        f"✅ Твій настрій: *{mood}*\n\nПартнер отримав повідомлення!",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="btn_main")]]),
    )


# ════════════════════════════════════════════════════════════════════════════════
# 🤖 ГОЛОВНА ФУНКЦІЯ 🤖
# ════════════════════════════════════════════════════════════════════════════════

def main() -> None:
    # ═══ ІНІЦІАЛІЗАЦІЯ БАЗИ ДАНИХ ═══
    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    media_filter = (
            filters.TEXT | filters.PHOTO | filters.VIDEO | filters.Sticker.ALL |
            filters.VOICE | filters.AUDIO | filters.Document.ALL | filters.VIDEO_NOTE
    )

    # ═══ CONVERSATION HANDLERS ═══
    send_conv = ConversationHandler(
        entry_points=[
            CommandHandler("send", send_command),
            CallbackQueryHandler(button_handler, pattern="^btn_send$"),
        ],
        states={
            SEND_RECIPIENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_get_recipient)],
            SEND_MESSAGE: [MessageHandler(media_filter & ~filters.COMMAND, send_deliver)],
        },
        fallbacks=[CommandHandler("cancel", send_cancel)],
        per_message=False,
    )

    reply_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(reply_button, pattern=r"^reply:\d+:.+$")],
        states={
            REPLY_MESSAGE: [MessageHandler(media_filter & ~filters.COMMAND, reply_deliver)],
        },
        fallbacks=[CommandHandler("cancel", reply_cancel)],
        per_message=False,
    )

    todo_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(todo_add_title, pattern="^todo_add$"),
            CommandHandler("todoadd", todo_add_title),
        ],
        states={
            TODO_ADD_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, todo_add_notes)],
            TODO_ADD_NOTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, todo_save)],
        },
        fallbacks=[CommandHandler("cancel", todo_cancel)],
        per_message=False,
    )

    timer_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(timer_add_prompt, pattern="^timer_add$"),
            CommandHandler("timer", show_timer_menu),
            CommandHandler("timeradd", timer_add_prompt),
        ],
        states={
            TIMER_SET_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, timer_set_date)],
            TIMER_SET_EVENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, timer_set_event)],
        },
        fallbacks=[CommandHandler("cancel", todo_cancel)],
        per_message=False,
    )

    love_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(love_write_prompt, pattern="^love_write$"),
            CommandHandler("lovenote", love_write_prompt),
        ],
        states={
            LOVE_NOTE_RECIPIENT: [CallbackQueryHandler(love_note_recipient_select, pattern="^love_(private|for:)")],
            LOVE_NOTE_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, love_save)],
        },
        fallbacks=[CommandHandler("cancel", todo_cancel)],
        per_message=False,
    )

    partner_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(partner_add_prompt, pattern="^partner_add_start$")],
        states={
            ADD_PARTNER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_partner_request)],
        },
        fallbacks=[CommandHandler("cancel", todo_cancel), CallbackQueryHandler(show_friends_menu, pattern="^btn_friends$")],
        per_message=False,
    )

    friend_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(friend_add_prompt, pattern="^friend_add_start$")],
        states={
            ADD_FRIEND_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, friend_add_action)],
        },
        fallbacks=[CommandHandler("cancel", todo_cancel), CallbackQueryHandler(show_friends_menu, pattern="^btn_friends$")],
        per_message=False,
    )

    # ═══ ДОДАЄМО ОБРОБНИКИ ═══
    app.add_handler(partner_conv)
    app.add_handler(friend_conv)
    app.add_handler(CallbackQueryHandler(accept_partner, pattern=r"^couple_accept:\d+$"))
    app.add_handler(CallbackQueryHandler(lambda u, c: u.callback_query.edit_message_text("❌ Запит відхилено."), pattern="^couple_decline$"))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", show_help))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("me", show_profile))
    app.add_handler(CommandHandler("block", block_user))
    app.add_handler(CommandHandler("unblock", unblock_user))
    app.add_handler(CommandHandler("blocklist", block_list))
    app.add_handler(CommandHandler("todo", todo_command))
    app.add_handler(CommandHandler("lovenote", love_note_command))
    app.add_handler(CommandHandler("friends", show_friends_menu))
    app.add_handler(CommandHandler("daily", daily_question_command))
    app.add_handler(CommandHandler("widget", show_partner_widget))
    app.add_handler(CommandHandler("mood", mood_command))

    app.add_handler(InlineQueryHandler(inline_query))

    # Conversation handlers
    app.add_handler(send_conv)
    app.add_handler(reply_conv)
    app.add_handler(todo_conv)
    app.add_handler(timer_conv)
    app.add_handler(love_conv)
    app.add_handler(friend_conv)

    # Callback handlers - МЕНЮ ТА ІНШЕ
    app.add_handler(CallbackQueryHandler(show_partner_widget, pattern="^btn_widget_"))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^btn_"))
    app.add_handler(CallbackQueryHandler(show_todos, pattern="^todo_show$"))
    app.add_handler(CallbackQueryHandler(show_timer_menu, pattern="^timer_details$"))
    app.add_handler(CallbackQueryHandler(love_note_nav, pattern="^love_(prev|next)$"))
    app.add_handler(CallbackQueryHandler(show_love_notes, pattern="^btn_love$"))
    app.add_handler(CallbackQueryHandler(show_friends_menu, pattern="^btn_friends$"))
    app.add_handler(CallbackQueryHandler(friend_sync, pattern="^friend_sync$"))
    app.add_handler(CallbackQueryHandler(sync_todos_all, pattern="^sync_todos$"))
    app.add_handler(CallbackQueryHandler(sync_timers_all, pattern="^sync_timers$"))
    app.add_handler(CallbackQueryHandler(show_profile, pattern="^btn_me$"))
    app.add_handler(CallbackQueryHandler(show_help, pattern="^btn_help$"))
    app.add_handler(CallbackQueryHandler(show_commands_menu, pattern="^btn_commands$"))

    # Видалення (вибіркове)
    app.add_handler(CallbackQueryHandler(todo_delete_menu, pattern="^todo_delete$"))
    app.add_handler(CallbackQueryHandler(todo_delete_action, pattern=r"^todo_del:\d+$"))
    app.add_handler(CallbackQueryHandler(timer_delete_menu, pattern="^timer_delete$"))
    app.add_handler(CallbackQueryHandler(timer_delete_action, pattern=r"^timer_del:\d+$"))

    # Позначення виконаних завдань
    app.add_handler(CallbackQueryHandler(todo_toggle_menu, pattern="^todo_toggle_menu$"))
    app.add_handler(CallbackQueryHandler(todo_toggle_action, pattern=r"^todo_tgl:\d+:(check|uncheck)$"))

    # Настрій
    app.add_handler(CallbackQueryHandler(mood_set_action, pattern=r"^mood_set:"))

    app.post_init = set_bot_commands

    logger.info("✅ Бот запущено!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
