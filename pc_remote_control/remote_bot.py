import asyncio
import os
import psutil
import time
import subprocess
import requests
import sys
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import FSInputFile, KeyboardButton, WebAppInfo
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv

load_dotenv()

# === НАЛАШТУВАННЯ ===
TOKEN = "8656323192:AAENdw0z62MstS-24w0xHJqX9wVyUTiRiiI"
ALLOWED_USER_ID = 2085927253
WEB_APP_URL = os.getenv("WEB_APP_URL", "")
PC_PASSWORD = os.getenv("PC_PASSWORD", "3451")
API_BASE_URL = "http://localhost:5000/api"

class States(StatesGroup):
    waiting_url = State()

bot = Bot(token=TOKEN)
dp = Dispatcher()

BUTTONS = {
    "SCREEN": "📸 Скріншот", "STATUS": "📊 Статус", "DISK": "📂 Диск",
    "VOL_UP": "🔊 +", "VOL_DOWN": "🔉 -", "MUTE": "🔇 Mute",
    "MEDIA_PRV": "⏮ Prev", "MEDIA_PP": "⏯ Play/Pause", "MEDIA_NXT": "⏭ Next",
    "YT": "🌐 YouTube", "STEAM": "🎮 Steam", "DISCORD": "👾 Discord",
    "TG": "✈️ Telegram", "OBSIDIAN": "📓 Obsidian", "BROWSER": "🌍 Google",
    "MON_ON": "🚨 Охорона Увімк.", "MON_OFF": "🛡 Охорона Вимк.",
    "SLEEP": "🌙 Сон", "WORK": "🚀 Робота", "OFF": "🛑 Вимкнути ПК", "CLICKER": "🖱 Автоклікер", "URL": "🔗 Відкрити URL",
    "ALBION": "⚔️ Albion Helper",
    "TERM": "💻 Термінал", "BT": "🔵 Bluetooth", "TRASH": "🗑 Кошик",
    "REMOTE": "🎮 Віддалене Керування"
}

def get_main_kb():
    builder = ReplyKeyboardBuilder()
    if WEB_APP_URL:
        builder.row(KeyboardButton(text="🚀 ВІДКРИТИ ПАНЕЛЬ", web_app=WebAppInfo(url=f"{WEB_APP_URL}/pc")))
        builder.row(KeyboardButton(text=BUTTONS["REMOTE"], web_app=WebAppInfo(url=f"{WEB_APP_URL}/remote")))

    builder.row(KeyboardButton(text=BUTTONS["SCREEN"]), KeyboardButton(text=BUTTONS["STATUS"]), KeyboardButton(text=BUTTONS["ALBION"]))
    builder.row(KeyboardButton(text=BUTTONS["VOL_UP"]), KeyboardButton(text=BUTTONS["VOL_DOWN"]), KeyboardButton(text=BUTTONS["MUTE"]))
    builder.row(KeyboardButton(text=BUTTONS["MEDIA_PRV"]), KeyboardButton(text=BUTTONS["MEDIA_PP"]), KeyboardButton(text=BUTTONS["MEDIA_NXT"]))
    builder.row(KeyboardButton(text=BUTTONS["WORK"]), KeyboardButton(text=BUTTONS["SLEEP"]), KeyboardButton(text=BUTTONS["OFF"]))
    builder.row(KeyboardButton(text=BUTTONS["TERM"]), KeyboardButton(text=BUTTONS["BT"]), KeyboardButton(text=BUTTONS["TRASH"]))
    builder.row(KeyboardButton(text=BUTTONS["YT"]), KeyboardButton(text=BUTTONS["URL"]), KeyboardButton(text=BUTTONS["DISCORD"]))
    builder.row(KeyboardButton(text=BUTTONS["TG"]), KeyboardButton(text=BUTTONS["OBSIDIAN"]), KeyboardButton(text=BUTTONS["STEAM"]))
    return builder.as_markup(resize_keyboard=True)

def get_xauth():
    """Динамічно знаходить XAUTHORITY файл"""
    result = subprocess.getoutput("ls /run/user/1000/xauth_* 2>/dev/null | head -1")
    return result.strip() or "/run/user/1000/xauth_DwEXMn"

async def run_shell(cmd: str):
    try:
        xauth = get_xauth()
        proc = await asyncio.create_subprocess_shell(
            f"DISPLAY=:0 XAUTHORITY={xauth} {cmd}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        return stdout.decode().strip() or stderr.decode().strip()
    except Exception as e: return f"Error: {e}"

# === ОБРОБНИКИ ===
@dp.message(Command("start"))
async def start(m: types.Message):
    if m.from_user.id == ALLOWED_USER_ID:
        await m.answer("🖥 ПК-Пульт (Nobara Edition) активовано!", reply_markup=get_main_kb())

@dp.message(F.text == BUTTONS["WORK"])
async def work_mode(m: types.Message):
    if m.from_user.id == ALLOWED_USER_ID:
        USER_ID = subprocess.getoutput("id -u")
        DBUS = f"unix:path=/run/user/{USER_ID}/bus"

        # Метод 1: Натискання пробілу (найнадійніший спосіб розбудити екран)
        await run_shell("xdotool key space")
        await asyncio.sleep(0.1)

        # Метод 2: Рух миші (додатковий спосіб)
        await run_shell("xdotool mousemove_relative -- 1 1")
        await asyncio.sleep(0.05)
        await run_shell("xdotool mousemove_relative -- -1 -1")
        await asyncio.sleep(0.1)

        # Метод 3: xset — вмикає DPMS / скидає таймер сну
        await run_shell("xset dpms force on")
        await run_shell("xset s reset")

        # Метод 4: gdbus — вимикає GNOME ScreenSaver без пароля
        await run_shell(
            f"DBUS_SESSION_BUS_ADDRESS={DBUS} "
            "gdbus call --session "
            "--dest org.gnome.ScreenSaver "
            "--object-path /org/gnome/ScreenSaver "
            "--method org.gnome.ScreenSaver.SetActive false"
        )

        # Яскравість на максимум
        await run_shell("brightnessctl set 100%")

        try: requests.post(f"{API_BASE_URL}/pc/scenario", json={"mode": "work"}, timeout=1)
        except: pass

        await m.answer("🚀 Робота! Екран ввімкнено та яскравість на макс.")

@dp.message(F.text == BUTTONS["SLEEP"])
async def sleep_mode(m: types.Message):
    if m.from_user.id == ALLOWED_USER_ID:
        await run_shell("brightnessctl set 0")
        await run_shell("xset dpms force off")

        try: requests.post(f"{API_BASE_URL}/pc/scenario", json={"mode": "sleep"}, timeout=1)
        except: pass

        await m.answer("🌙 Сон! Екран вимкнено.")

@dp.message(F.text == BUTTONS["ALBION"])
async def albion_launch(m: types.Message):
    if m.from_user.id == ALLOWED_USER_ID:
        requests.post(f"{API_BASE_URL}/pc/albion")
        await m.answer("⚔️ Albion Helper запущено!")

@dp.message(F.text == BUTTONS["TERM"])
async def open_term(m: types.Message):
    if m.from_user.id == ALLOWED_USER_ID:
        await run_shell("gnome-terminal &")
        await m.answer("💻 Термінал запущено!")

@dp.message(F.text == BUTTONS["BT"])
async def toggle_bt(m: types.Message):
    if m.from_user.id == ALLOWED_USER_ID:
        await run_shell("bluetoothctl power on" if "off" in await run_shell("bluetoothctl show") else "bluetoothctl power off")
        await m.answer("🔵 Стан Bluetooth змінено!")

@dp.message(F.text == BUTTONS["TRASH"])
async def empty_trash(m: types.Message):
    if m.from_user.id == ALLOWED_USER_ID:
        await run_shell("rm -rf ~/.local/share/Trash/*")
        await m.answer("🗑 Кошик очищено!")

@dp.message(F.text == BUTTONS["SCREEN"])
async def screen(m: types.Message):
    if m.from_user.id != ALLOWED_USER_ID: return
    await m.answer("📸 Роблю скріншот...")
    requests.post(f"{API_BASE_URL}/pc/screenshot", json={"user_id": m.from_user.id, "password": PC_PASSWORD})

@dp.message(F.text == BUTTONS["URL"])
async def url_req(m: types.Message, state: FSMContext):
    if m.from_user.id == ALLOWED_USER_ID:
        await m.answer("🔗 Відправити посилання:"); await state.set_state(States.waiting_url)

@dp.message(States.waiting_url)
async def url_done(m: types.Message, state: FSMContext):
    url = m.text if m.text.startswith("http") else f"https://{m.text}"
    await run_shell(f"xdg-open {url}")
    await state.clear(); await m.answer("🌐 Відкрито в браузері!")

@dp.message(F.text.in_({BUTTONS["MEDIA_PRV"], BUTTONS["MEDIA_PP"], BUTTONS["MEDIA_NXT"]}))
async def media_ctrl(m: types.Message):
    if m.from_user.id != ALLOWED_USER_ID: return
    cmd = "play-pause" if m.text == BUTTONS["MEDIA_PP"] else "next" if m.text == BUTTONS["MEDIA_NXT"] else "previous"
    await run_shell(f"playerctl {cmd}")
    await m.answer(m.text)

@dp.message(F.text == BUTTONS["OFF"])
async def off_req(m: types.Message):
    if m.from_user.id == ALLOWED_USER_ID:
        await m.answer("🛑 ПК вимкнеться через хвилину..."); await run_shell("shutdown +1")

@dp.message(F.text == BUTTONS["YT"])
async def open_yt(m: types.Message): await run_shell("xdg-open https://youtube.com"); await m.answer("🌐 YouTube")

@dp.message(F.text == BUTTONS["TG"])
async def open_tg(m: types.Message): await run_shell("flatpak run org.telegram.desktop &"); await m.answer("✈️ Telegram")

@dp.message(F.text.in_({BUTTONS["VOL_UP"], BUTTONS["VOL_DOWN"], BUTTONS["MUTE"]}))
async def vol(m: types.Message):
    if BUTTONS["VOL_UP"] in m.text: await run_shell("wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%+")
    elif BUTTONS["VOL_DOWN"] in m.text: await run_shell("wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-")
    else: await run_shell("wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle")
    await m.answer(m.text)

@dp.message(F.text == BUTTONS["STATUS"])
async def stat(m: types.Message):
    status_text = f"🖥 CPU: {psutil.cpu_percent()}% | RAM: {psutil.virtual_memory().percent}%"
    await m.answer(status_text)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())