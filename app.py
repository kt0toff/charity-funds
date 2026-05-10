import os
import sys
import sqlite3
import psutil
import cv2
import threading
import time
import requests
import subprocess
import logging
import json
from collections import defaultdict
from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS
from datetime import datetime, timedelta
from dotenv import load_dotenv
from functools import wraps

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# Розширені CORS налаштування для роботи з Telegram Web App
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "expose_headers": ["Content-Type"],
        "supports_credentials": False
    }
})

# Middleware для логування запитів
@app.before_request
def log_request_info():
    """Логує інформацію про кожен запит"""
    client_ip = request.remote_addr
    path = request.path
    method = request.method

    # Логуємо тільки API запити, щоб не засмічувати логи статикою
    if path.startswith('/api/'):
        logger.info(f"Request: {method} {path} from {client_ip}")

@app.after_request
def add_security_headers(response):
    """Додає security headers"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

DB_PATH = 'bot_data.db'
PC_BOT_TOKEN = os.getenv("PC_BOT_TOKEN", "")
PC_USER_ID = int(os.getenv("PC_USER_ID", "0"))
PC_PASSWORD = os.getenv("PC_PASSWORD", "3451")

rate_limit_store = defaultdict(list)
RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX_REQUESTS = 30

SCHEDULER_FILE = 'scheduled_tasks.json'
scheduled_tasks = []

# Історія метрик для графіків (зберігаємо останню годину)
metrics_history = {
    'cpu': [],
    'ram': [],
    'timestamps': []
}
MAX_HISTORY_POINTS = 60  # 60 точок = 1 година при оновленні кожні 60 секунд

def rate_limit(f):
    """Rate limiting декоратор для захисту від зловживань"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_ip = request.remote_addr
        now = time.time()

        rate_limit_store[client_ip] = [
            req_time for req_time in rate_limit_store[client_ip]
            if now - req_time < RATE_LIMIT_WINDOW
        ]

        if len(rate_limit_store[client_ip]) >= RATE_LIMIT_MAX_REQUESTS:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return jsonify({"error": "Too many requests. Please try again later."}), 429

        rate_limit_store[client_ip].append(now)
        return f(*args, **kwargs)
    return decorated_function

def get_db_connection():
    """Створює з'єднання з базою даних з автоматичним перетворенням рядків у словники"""
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logger.error(f"Database connection error: {e}")
        raise

def require_auth(f):
    """Декоратор для перевірки авторизації"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header == f"Bearer {PC_PASSWORD}":
            return f(*args, **kwargs)

        password = request.args.get("password") or (request.json or {}).get("password")
        if password and password == PC_PASSWORD:
            return f(*args, **kwargs)

        user_id = request.args.get("user_id") or (request.json or {}).get("user_id")
        if user_id and int(user_id) == PC_USER_ID:
            return f(*args, **kwargs)

        return jsonify({"error": "Unauthorized"}), 401
    return decorated_function

def validate_json(required_fields=None):
    """Валідація JSON запитів"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return jsonify({"error": "Content-Type must be application/json"}), 400

            data = request.json
            if required_fields:
                missing = [field for field in required_fields if field not in data]
                if missing:
                    return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Створення таблиці гри, якщо вона не існує
def init_game_db():
    """Ініціалізація таблиці гри з обробкою помилок"""
    try:
        conn = get_db_connection()
        conn.execute('''CREATE TABLE IF NOT EXISTS game_state
                        (user_id INTEGER PRIMARY KEY, state_json TEXT, last_updated DATETIME)''')
        conn.commit()
        conn.close()
        logger.info("Game database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize game database: {e}")
        raise

init_game_db()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint для моніторингу"""
    try:
        conn = get_db_connection()
        conn.execute("SELECT 1").fetchone()
        conn.close()
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"

    return jsonify({
        "status": "ok" if db_status == "healthy" else "degraded",
        "timestamp": datetime.now().isoformat(),
        "database": db_status,
        "uptime": int(time.time() - app.config.get('START_TIME', time.time())),
        "motion_detector": motion_enabled,
        "streaming": is_streaming
    }), 200 if db_status == "healthy" else 503

app.config['START_TIME'] = time.time()

# ─── ГРА NEURAL ARCHITECT ──────────────────────────────────────────────────

@app.route('/api/game/load', methods=['GET'])
@rate_limit
def game_load():
    try:
        user_id = request.args.get("user_id", PC_USER_ID)
        if not user_id:
            return jsonify({"error": "user_id is required"}), 400

        conn = get_db_connection()
        row = conn.execute("SELECT state_json FROM game_state WHERE user_id = ?", (user_id,)).fetchone()
        conn.close()

        if row:
            return jsonify({"state": row['state_json'], "success": True})
        return jsonify({"state": None, "success": True})
    except Exception as e:
        logger.error(f"Error loading game state: {e}")
        return jsonify({"error": "Failed to load game state"}), 500

@app.route('/api/game/save', methods=['POST'])
@rate_limit
@validate_json(['state'])
def game_save():
    try:
        data = request.json
        user_id = data.get("user_id", PC_USER_ID)
        state = data.get("state")

        if not state:
            return jsonify({"error": "No state provided"}), 400

        conn = get_db_connection()
        conn.execute('''INSERT INTO game_state (user_id, state_json, last_updated)
                        VALUES (?, ?, ?)
                        ON CONFLICT(user_id) DO UPDATE SET state_json=excluded.state_json, last_updated=excluded.last_updated''',
                     (user_id, state, datetime.now()))
        conn.commit()
        conn.close()
        logger.info(f"Game state saved for user {user_id}")
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error saving game state: {e}")
        return jsonify({"error": "Failed to save game state"}), 500

@app.route('/game')
def game_page():
    return send_file('game.html')

def get_gui_env():
    uid = os.getuid()
    env = os.environ.copy()
    env["DISPLAY"] = ":0"
    if os.path.exists(f"/run/user/{uid}/wayland-0"):
        env["WAYLAND_DISPLAY"] = "wayland-0"
    elif os.path.exists(f"/run/user/{uid}/wayland-1"):
        env["WAYLAND_DISPLAY"] = "wayland-1"
    env["XDG_RUNTIME_DIR"] = f"/run/user/{uid}"
    env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path=/run/user/{uid}/bus"
    return env

# ─── МОНІТОРИНГ ───────────────────────────────────────────────────────────
motion_enabled = False
is_streaming = False

def motion_detector_thread():
    global motion_enabled, is_streaming
    last_frame = None
    cap = None
    while True:
        try:
            if motion_enabled and not is_streaming:
                if cap is None or not cap.isOpened():
                    cap = cv2.VideoCapture(0)
                    time.sleep(2) # Затримка для ініціалізації камери
                    continue
                ret, frame = cap.read()
                if not ret:
                    continue
                gray = cv2.GaussianBlur(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (21, 21), 0)
                if last_frame is None:
                    last_frame = gray
                    time.sleep(1)
                    continue
                delta = cv2.absdiff(last_frame, gray)
                thresh = cv2.dilate(cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)[1], None, iterations=2)
                cnts, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if any(cv2.contourArea(c) > 5000 for c in cnts):
                    p_path = "/tmp/alert.jpg"
                    cv2.imwrite(p_path, frame)
                    with open(p_path, "rb") as f:
                        requests.post(
                            f"https://api.telegram.org/bot{PC_BOT_TOKEN}/sendPhoto",
                            data={"chat_id": PC_USER_ID, "caption": "🚨 РУХ!"},
                            files={"photo": f},
                        )
                    if os.path.exists(p_path): os.remove(p_path)
                    time.sleep(15) # Кулдаун після виявлення руху
                last_frame = gray
                time.sleep(0.5) # Пауза між кадрами
            else:
                if cap is not None:
                    cap.release()
                    cap = None
                last_frame = None
                time.sleep(2)
        except Exception:
            if cap is not None:
                cap.release()
                cap = None
            time.sleep(5)

threading.Thread(target=motion_detector_thread, daemon=True).start()

# ─── API ──────────────────────────────────────────────────────────────────

@app.route('/api/pc/stats', methods=['GET'])
@rate_limit
def pc_stats():
    global metrics_history
    try:
        temp = 0
        try:
            if os.path.exists("/sys/class/thermal/thermal_zone0/temp"):
                with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                    temp = int(f.read().strip()) // 1000
        except Exception as e:
            logger.warning(f"Failed to read temperature: {e}")

        cpu_percent = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        # Зберігаємо в історію
        metrics_history['cpu'].append(cpu_percent)
        metrics_history['ram'].append(ram.percent)
        metrics_history['timestamps'].append(datetime.now().isoformat())

        # Обмежуємо розмір історії
        if len(metrics_history['cpu']) > MAX_HISTORY_POINTS:
            metrics_history['cpu'].pop(0)
            metrics_history['ram'].pop(0)
            metrics_history['timestamps'].pop(0)

        return jsonify({
            "cpu": cpu_percent,
            "ram": ram.percent,
            "ram_used_gb": round(ram.used / (1024**3), 2),
            "ram_total_gb": round(ram.total / (1024**3), 2),
            "disk": disk.percent,
            "disk_used_gb": round(disk.used / (1024**3), 2),
            "disk_total_gb": round(disk.total / (1024**3), 2),
            "temp": temp,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting PC stats: {e}")
        return jsonify({"error": "Failed to retrieve system stats"}), 500

@app.route('/api/pc/stats/history', methods=['GET'])
@rate_limit
def pc_stats_history():
    """Отримати історію метрик для графіків"""
    try:
        return jsonify({
            "cpu": metrics_history['cpu'],
            "ram": metrics_history['ram'],
            "timestamps": metrics_history['timestamps'],
            "success": True
        })
    except Exception as e:
        logger.error(f"Error getting stats history: {e}")
        return jsonify({"error": "Failed to retrieve stats history"}), 500

@app.route('/api/pc/power', methods=['POST'])
@rate_limit
@require_auth
def pc_pwr():
    try:
        d = request.json or {}
        a = d.get("action")
        allowed = {"shutdown", "reboot", "sleep"}

        if a not in allowed:
            return jsonify({"error": f"Unknown action. Allowed: {', '.join(allowed)}"}), 400

        logger.warning(f"Power action requested: {a} from {request.remote_addr}")

        if a == "sleep":
            subprocess.run(["busctl", "--user", "call", "org.kde.kglobalaccel",
                            "/component/org_kde_powerdevil", "org.kde.kglobalaccel.Component",
                            "invokeShortcut", "s", "Turn Off Screen"], env=get_gui_env(), check=False)
            return jsonify({"success": True, "action": a})

        if a == "shutdown":
            subprocess.run(["shutdown", "+1"], check=False)
        elif a == "reboot":
            subprocess.run(["reboot"], check=False)

        return jsonify({"success": True, "action": a})
    except Exception as e:
        logger.error(f"Power action failed: {e}")
        return jsonify({"error": "Failed to execute power action"}), 500

@app.route('/api/pc/screenshot', methods=['POST'])
@rate_limit
@require_auth
def pc_ss():
    try:
        d = request.json or {}
        path = "/tmp/ss.png"

        if os.path.exists(path):
            os.remove(path)

        res = subprocess.run(
            ["spectacle", "-b", "-n", "-o", path],
            env=get_gui_env(), check=False, capture_output=True, text=True, timeout=10
        )

        time.sleep(1)

        if os.path.exists(path):
            chat_id = d.get("user_id", PC_USER_ID)
            with open(path, "rb") as f:
                response = requests.post(
                    f"https://api.telegram.org/bot{PC_BOT_TOKEN}/sendPhoto",
                    data={"chat_id": chat_id},
                    files={"photo": f},
                    timeout=30
                )
                response.raise_for_status()

            logger.info(f"Screenshot sent to user {chat_id}")
            return jsonify({"success": True})

        logger.error(f"Screenshot failed: {res.stderr}")
        return jsonify({"error": f"Screenshot failed: {res.stderr}"}), 500
    except subprocess.TimeoutExpired:
        logger.error("Screenshot timeout")
        return jsonify({"error": "Screenshot timeout"}), 500
    except requests.RequestException as e:
        logger.error(f"Failed to send screenshot: {e}")
        return jsonify({"error": "Failed to send screenshot to Telegram"}), 500
    except Exception as e:
        logger.error(f"Screenshot error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/pc/brightness', methods=['POST'])
@rate_limit
def pc_brightness():
    d = request.json or {}
    val = max(0, min(100, int(d.get("value", 50))))
    try:
        env = get_gui_env()

        if val == 0:
            # Вимикаємо екран через KDE
            subprocess.run(["busctl", "--user", "call", "org.kde.kglobalaccel",
                            "/component/org_kde_powerdevil", "org.kde.kglobalaccel.Component",
                            "invokeShortcut", "s", "Turn Off Screen"], env=env, check=False)
        else:
            # Будимо екран перед зміною яскравості
            subprocess.run(["xdotool", "mousemove_relative", "--", "1", "1"], env=env, check=False)
            subprocess.run(["xdotool", "mousemove_relative", "--", "-1", "-1"], env=env, check=False)

            subprocess.run(["busctl", "--user", "call", "org.freedesktop.ScreenSaver",
                            "/ScreenSaver", "org.freedesktop.ScreenSaver",
                            "SimulateUserActivity"], env=env, check=False)

            time.sleep(0.3)

            # Встановлюємо яскравість
            kde_val = val * 100
            subprocess.run(
                ["busctl", "--user", "call",
                 "org.kde.Solid.PowerManagement",
                 "/org/kde/Solid/PowerManagement/Actions/BrightnessControl",
                 "org.kde.Solid.PowerManagement.Actions.BrightnessControl",
                 "setBrightness", "i", str(kde_val)],
                env=env, check=False,
            )

        logger.info(f"Brightness set to {val}%")
        return jsonify({"success": True, "brightness": val})
    except Exception as e:
        logger.error(f"Brightness control failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/pc/process/kill', methods=['POST'])
@rate_limit
@require_auth
def pc_process_kill():
    try:
        d = request.json or {}
        pid = d.get("pid")

        if not pid:
            return jsonify({"error": "No PID provided"}), 400

        try:
            pid = int(pid)
        except ValueError:
            return jsonify({"error": "Invalid PID format"}), 400

        p = psutil.Process(pid)
        process_name = p.name()

        logger.warning(f"Killing process {process_name} (PID: {pid})")

        p.terminate()
        try:
            p.wait(timeout=3)
        except psutil.TimeoutExpired:
            p.kill()

        return jsonify({"success": True, "pid": pid, "name": process_name})
    except psutil.NoSuchProcess:
        return jsonify({"error": "Process not found"}), 404
    except psutil.AccessDenied:
        return jsonify({"error": "Access denied"}), 403
    except Exception as e:
        logger.error(f"Failed to kill process: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/pc/media', methods=['POST'])
@require_auth
def pc_media():
    d = request.json or {}
    action = d.get("action")
    allowed = {"play-pause", "next", "previous"}
    if action in allowed:
        subprocess.run(["playerctl", action], env=get_gui_env(), check=False)
        return jsonify({"success": True})
    return jsonify({"error": "Unknown action"}), 400

@app.route('/api/pc/open_url', methods=['POST'])
@rate_limit
def pc_open_url():
    try:
        d = request.json or {}
        url = d.get("url", "")

        if not url:
            return jsonify({"error": "No URL provided"}), 400

        if not (url.startswith("http://") or url.startswith("https://")):
            return jsonify({"error": "Invalid URL protocol. Must be http:// or https://"}), 400

        if len(url) > 2048:
            return jsonify({"error": "URL too long"}), 400

        subprocess.run(["xdg-open", url], env=get_gui_env(), check=False, timeout=5)
        logger.info(f"Opened URL: {url[:100]}")
        return jsonify({"success": True, "url": url})
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Timeout opening URL"}), 500
    except Exception as e:
        logger.error(f"Failed to open URL: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/pc/video_feed')
def video_feed():
    def gen():
        global is_streaming
        is_streaming = True
        c = cv2.VideoCapture(0)
        try:
            while is_streaming:
                r, f = c.read()
                if not r: break
                _, b = cv2.imencode('.jpg', f, [cv2.IMWRITE_JPEG_QUALITY, 50])
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + b.tobytes() + b'\r\n')
        finally:
            c.release()
            is_streaming = False
    return make_response(app.response_class(gen(), mimetype='multipart/x-mixed-replace; boundary=frame'))

@app.route('/api/pc/screen_capture')
@require_auth
def screen_capture():
    """Швидкий скріншот для трансляції"""
    try:
        path = "/tmp/screen_live.jpg"
        env = get_gui_env()

        # Спробуємо scrot (швидший), якщо не вийде - spectacle
        scrot_success = False
        try:
            result = subprocess.run(
                ["scrot", "-o", "-q", "70", path],
                check=True,
                timeout=1,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            scrot_success = (result.returncode == 0 and os.path.exists(path))
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            scrot_success = False

        # Якщо scrot не спрацював, використовуємо spectacle
        if not scrot_success:
            subprocess.run(
                ["spectacle", "-b", "-n", "-o", path],
                env=env,
                check=False,
                timeout=2,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            time.sleep(0.15)

        if os.path.exists(path):
            # Перевіряємо чи потрібна оптимізація (тільки якщо файл > 500KB)
            file_size = os.path.getsize(path)
            if file_size > 500000:  # 500KB
                try:
                    img = cv2.imread(path)
                    if img is not None:
                        height, width = img.shape[:2]
                        # Зменшуємо тільки якщо ширина > 1920
                        if width > 1920:
                            scale = 1920 / width
                            new_width = 1920
                            new_height = int(height * scale)
                            img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
                            cv2.imwrite(path, img, [cv2.IMWRITE_JPEG_QUALITY, 75])
                            logger.info(f"Image optimized: {width}x{height} -> {new_width}x{new_height}")
                except Exception as e:
                    logger.warning(f"Image optimization failed: {e}")

            return send_file(path, mimetype='image/jpeg', max_age=0)
        else:
            logger.error("Screenshot file not created")
            return jsonify({"error": "Screenshot failed"}), 500
    except Exception as e:
        logger.error(f"Screen capture error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/pc/screen_stream')
def screen_stream():
    """Трансляція екрану через FFmpeg"""
    def gen():
        global is_streaming
        is_streaming = True
        env = get_gui_env()

        cmd = [
            'ffmpeg',
            '-f', 'x11grab',
            '-video_size', '1280x720',
            '-framerate', '8',
            '-i', ':0.0',
            '-q:v', '8',
            '-f', 'image2pipe',
            '-vcodec', 'mjpeg',
            '-'
        ]

        process = None
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                env=env,
                bufsize=0
            )

            while is_streaming and process.poll() is None:
                try:
                    # Читаємо JPEG маркери з таймаутом
                    jpeg_start = process.stdout.read(2)
                    if not jpeg_start or jpeg_start != b'\xff\xd8':
                        continue

                    # Читаємо до кінця JPEG
                    jpeg_data = jpeg_start
                    max_size = 500000  # 500KB max
                    while len(jpeg_data) < max_size:
                        byte = process.stdout.read(1)
                        if not byte:
                            break
                        jpeg_data += byte
                        if len(jpeg_data) >= 2 and jpeg_data[-2:] == b'\xff\xd9':
                            break

                    if len(jpeg_data) > 2:
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' +
                               jpeg_data + b'\r\n')
                except Exception as e:
                    logger.error(f"Frame read error: {e}")
                    break

        except Exception as e:
            logger.error(f"Screen streaming error: {e}")
        finally:
            is_streaming = False
            if process:
                try:
                    process.terminate()
                    process.wait(timeout=1)
                except:
                    try:
                        process.kill()
                    except:
                        pass

    response = make_response(gen())
    response.headers['Content-Type'] = 'multipart/x-mixed-replace; boundary=frame'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/api/pc/screenshot_stream')
def screenshot_stream():
    """Швидкий скріншот для трансляції"""
    try:
        import tempfile
        env = get_gui_env()

        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp_path = tmp.name

        # Швидкий скріншот через FFmpeg
        subprocess.run(
            ['ffmpeg', '-f', 'x11grab', '-video_size', '1920x1080',
             '-i', ':0.0', '-vframes', '1', '-q:v', '3', '-y', tmp_path],
            env=env,
            capture_output=True,
            timeout=2
        )

        if os.path.exists(tmp_path):
            response = send_file(tmp_path, mimetype='image/jpeg')
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'

            # Видаляємо файл після відправки
            @response.call_on_close
            def cleanup():
                try:
                    os.remove(tmp_path)
                except:
                    pass

            return response

        return jsonify({"error": "Failed to capture screenshot"}), 500
    except Exception as e:
        logger.error(f"Screenshot stream error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/pc/screen_stream/stop', methods=['POST'])
def stop_screen_stream():
    """Зупинити трансляцію екрану"""
    global is_streaming
    is_streaming = False
    return jsonify({"success": True})

@app.route('/api/pc/mouse', methods=['POST'])
@require_auth
def pc_mouse():
    """Керування мишею"""
    try:
        data = request.json or {}
        action = data.get('action')
        env = get_gui_env()

        if action == 'move':
            x = data.get('x', 0)
            y = data.get('y', 0)
            subprocess.run(['xdotool', 'mousemove', str(x), str(y)], env=env, check=False)

        elif action == 'move_relative':
            dx = data.get('dx', 0)
            dy = data.get('dy', 0)
            subprocess.run(['xdotool', 'mousemove_relative', '--', str(dx), str(dy)], env=env, check=False)

        elif action == 'click':
            button = data.get('button', 1)  # 1=left, 2=middle, 3=right
            subprocess.run(['xdotool', 'click', str(button)], env=env, check=False)

        elif action == 'scroll':
            direction = data.get('direction', 'up')  # up/down
            amount = data.get('amount', 1)
            button = '4' if direction == 'up' else '5'
            for _ in range(amount):
                subprocess.run(['xdotool', 'click', button], env=env, check=False)

        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Mouse control error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/pc/keyboard', methods=['POST'])
@require_auth
def pc_keyboard():
    """Керування клавіатурою"""
    try:
        data = request.json or {}
        action = data.get('action')
        env = get_gui_env()

        if action == 'type':
            text = data.get('text', '')
            subprocess.run(['xdotool', 'type', '--', text], env=env, check=False)

        elif action == 'key':
            key = data.get('key', '')
            subprocess.run(['xdotool', 'key', key], env=env, check=False)

        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Keyboard control error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/pc/motion/toggle', methods=['POST'])
@rate_limit
def mt():
    global motion_enabled
    motion_enabled = not motion_enabled
    logger.info(f"Motion detection {'enabled' if motion_enabled else 'disabled'}")
    return jsonify({"motion_enabled": motion_enabled, "success": True})


@app.route('/api/pc/system/info', methods=['GET'])
@rate_limit
def system_info():
    """Розширена інформація про систему"""
    try:
        import platform
        boot_time = datetime.fromtimestamp(psutil.boot_time())

        return jsonify({
            "hostname": platform.node(),
            "platform": platform.system(),
            "platform_release": platform.release(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "boot_time": boot_time.isoformat(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "cpu_freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
        })
    except Exception as e:
        logger.error(f"Failed to get system info: {e}")
        return jsonify({"error": "Failed to retrieve system info"}), 500


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {e}")
    return jsonify({"error": "Internal server error"}), 500


@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled exception: {e}", exc_info=True)
    return jsonify({"error": "An unexpected error occurred"}), 500


@app.route('/api/pc/scenario', methods=['POST'])
@rate_limit
def pc_scenario_v2():
    data = request.json or {}
    mode = data.get("mode")
    env = get_gui_env()
    try:
        if mode == 'sleep':
            # Вимикаємо екран через KDE
            subprocess.run(["busctl", "--user", "call", "org.kde.kglobalaccel",
                            "/component/org_kde_powerdevil", "org.kde.kglobalaccel.Component",
                            "invokeShortcut", "s", "Turn Off Screen"], env=env, check=False)
            logger.info("Sleep scenario activated")
        elif mode == 'work':
            # Будимо монітори рухом миші
            subprocess.run(["xdotool", "mousemove_relative", "--", "1", "1"], env=env, check=False)
            subprocess.run(["xdotool", "mousemove_relative", "--", "-1", "-1"], env=env, check=False)

            subprocess.run(["busctl", "--user", "call", "org.freedesktop.ScreenSaver",
                            "/ScreenSaver", "org.freedesktop.ScreenSaver",
                            "SimulateUserActivity"], env=env, check=False)

            time.sleep(0.3)

            # Встановлюємо яскравість на 80%
            subprocess.run(
                ["busctl", "--user", "call",
                 "org.kde.Solid.PowerManagement",
                 "/org/kde/Solid/PowerManagement/Actions/BrightnessControl",
                 "org.kde.Solid.PowerManagement.Actions.BrightnessControl",
                 "setBrightness", "i", "8000"],
                env=env, check=False,
            )

            subprocess.run(["rfkill", "unblock", "bluetooth"], check=False)
            subprocess.run(["gsettings", "set", "org.gnome.settings-daemon.plugins.color",
                            "night-light-enabled", "false"], env=env, check=False)
            subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "50%"], env=env, check=False)
            logger.info("Work scenario activated")
        return jsonify({"success": True, "mode": mode})
    except Exception as e:
        logger.error(f"Scenario failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/pc/volume', methods=['GET'])
def pc_volume_get():
    try:
        out = subprocess.check_output(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"],
                                      text=True, env=get_gui_env())
        parts = out.strip().split()
        vol = int(float(parts[1]) * 100) if len(parts) >= 2 else 50
        muted = "MUTED" in out
        return jsonify({"volume": vol, "muted": muted})
    except Exception:
        return jsonify({"volume": 50, "muted": False})


@app.route('/api/pc/volume', methods=['POST'])
def pc_volume_set():
    d = request.json or {}
    vol = d.get("volume", 50)
    try:
        vol = max(0, min(100, int(vol)))
        subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{vol}%"],
                       env=get_gui_env(), check=False)
        return jsonify({"success": True, "volume": vol})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/pc/mute', methods=['POST'])
def pc_mute_toggle():
    try:
        subprocess.run(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"],
                       env=get_gui_env(), check=False)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/pc/lock', methods=['POST'])
def pc_lock():
    try:
        subprocess.run(["loginctl", "lock-session"], env=get_gui_env(), check=False)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/pc/notify', methods=['POST'])
def pc_notify():
    d = request.json or {}
    title = d.get("title", "Сповіщення")
    body = d.get("body", "")
    try:
        subprocess.run(["notify-send", "--urgency=normal", title, body],
                       env=get_gui_env(), check=False)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/pc/clipboard', methods=['POST'])
def pc_clipboard():
    d = request.json or {}
    text = d.get("text", "")
    if not text:
        return jsonify({"error": "No text"}), 400
    try:
        env = get_gui_env()
        proc = subprocess.Popen(["xclip", "-selection", "clipboard"],
                                stdin=subprocess.PIPE, env=env)
        proc.communicate(text.encode())
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/pc/linux/terminal', methods=['POST'])
def pc_terminal():
    try:
        subprocess.Popen(["ptyxis"], start_new_session=True, env=get_gui_env())
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/pc/linux/trash', methods=['POST'])
def pc_trash():
    try:
        trash_dir = os.path.expanduser("~/.local/share/Trash")
        for sub in ["files", "info"]:
            d = os.path.join(trash_dir, sub)
            if os.path.exists(d):
                for f in os.listdir(d):
                    p = os.path.join(d, f)
                    if os.path.isdir(p):
                        import shutil; shutil.rmtree(p)
                    else:
                        os.remove(p)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/pc/linux/bluetooth', methods=['POST'])
def pc_bluetooth():
    try:
        subprocess.run(["rfkill", "toggle", "bluetooth"], check=False)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/pc/processes', methods=['GET'])
def pc_processes():
    try:
        procs = []
        for p in sorted(psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']),
                        key=lambda x: x.info['cpu_percent'] or 0, reverse=True)[:10]:
            procs.append({
                "pid": p.info['pid'],
                "name": p.info['name'],
                "cpu": round(p.info['cpu_percent'] or 0, 1),
                "mem": round(p.info['memory_percent'] or 0, 1),
            })
        return jsonify(procs)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/pc/network', methods=['GET'])
def pc_network():
    try:
        net = psutil.net_io_counters()
        return jsonify({
            "sent_mb": round(net.bytes_sent / 1024 / 1024, 1),
            "recv_mb": round(net.bytes_recv / 1024 / 1024, 1),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/pc/uptime', methods=['GET'])
def pc_uptime():
    try:
        boot = psutil.boot_time()
        uptime_sec = int(time.time() - boot)
        h = uptime_sec // 3600
        m = (uptime_sec % 3600) // 60
        return jsonify({"uptime": f"{h}г {m}хв", "uptime_sec": uptime_sec})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/pc/id', methods=['GET'])
def get_pc_id():
    return jsonify({"pc_id": "CLASSIC"})

@app.route('/api/pc/albion', methods=['POST'])
def launch_albion_helper():
    try:
        import sys
        import os
        base_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(base_dir, "albion_helper.py")
        log_path = os.path.join(base_dir, "albion_error.log")
        
        if not os.path.exists(script_path):
            return jsonify({"error": f"File not found: {script_path}"}), 404

        env = get_gui_env()
        # Забезпечуємо доступ до встановлених пакетів у venv
        env['PYTHONPATH'] = os.pathsep.join(sys.path)

        with open(log_path, "a") as log_file:
            log_file.write(f"\n--- Launching Albion Helper at {time.ctime()} ---\n")
            subprocess.Popen([sys.executable, script_path], 
                             env=env, 
                             cwd=base_dir,
                             start_new_session=True,
                             stdout=log_file,
                             stderr=log_file)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/pc/test_launch', methods=['POST'])
def test_launch():
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(base_dir, "test_launch.py")
        subprocess.Popen([sys.executable, script_path], start_new_session=True)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def idx():
    return send_file('mini_app.html')


@app.route('/pc')
def pc_page():
    return send_file('pc_app.html')

@app.route('/remote')
def remote_control_page():
    return send_file('remote_control.html')

@app.route('/remote2')
def remote_control_page_v2():
    return send_file('remote_control_v2.html')


# ─── SCHEDULER ────────────────────────────────────────────────────────────

def load_scheduled_tasks():
    """Завантажує заплановані задачі з файлу"""
    global scheduled_tasks
    if os.path.exists(SCHEDULER_FILE):
        try:
            with open(SCHEDULER_FILE, 'r') as f:
                scheduled_tasks = json.load(f)
            logger.info(f"Loaded {len(scheduled_tasks)} scheduled tasks")
        except Exception as e:
            logger.error(f"Failed to load scheduled tasks: {e}")
            scheduled_tasks = []
    else:
        scheduled_tasks = []

def save_scheduled_tasks():
    """Зберігає заплановані задачі у файл"""
    try:
        with open(SCHEDULER_FILE, 'w') as f:
            json.dump(scheduled_tasks, f, indent=2)
        logger.info("Scheduled tasks saved")
    except Exception as e:
        logger.error(f"Failed to save scheduled tasks: {e}")

def execute_scheduled_task(task):
    """Виконує заплановану задачу"""
    try:
        task_type = task.get('type')
        env = get_gui_env()

        if task_type == 'launch_app':
            app_path = task.get('app_path')
            subprocess.Popen([app_path], env=env, start_new_session=True)
            logger.info(f"Launched app: {app_path}")

        elif task_type == 'shutdown':
            subprocess.run(["shutdown", "+1"], check=False)
            logger.warning("Shutdown scheduled")

        elif task_type == 'reboot':
            subprocess.run(["reboot"], check=False)
            logger.warning("Reboot scheduled")

        # Видаляємо одноразову задачу
        if not task.get('recurring', False):
            scheduled_tasks.remove(task)
            save_scheduled_tasks()

    except Exception as e:
        logger.error(f"Failed to execute scheduled task: {e}")

def scheduler_thread():
    """Потік для перевірки запланованих задач"""
    logger.info("Scheduler thread started")
    while True:
        try:
            now = datetime.now()
            for task in scheduled_tasks[:]:
                scheduled_time = datetime.fromisoformat(task.get('scheduled_time'))

                if now >= scheduled_time:
                    execute_scheduled_task(task)

            time.sleep(30)  # Перевіряємо кожні 30 секунд
        except Exception as e:
            logger.error(f"Scheduler thread error: {e}")
            time.sleep(60)

@app.route('/api/pc/scheduler/tasks', methods=['GET'])
@rate_limit
def get_scheduled_tasks():
    """Отримати список запланованих задач"""
    return jsonify({"tasks": scheduled_tasks, "success": True})

@app.route('/api/pc/scheduler/add', methods=['POST'])
@rate_limit
@require_auth
def add_scheduled_task():
    """Додати нову заплановану задачу"""
    try:
        data = request.json or {}
        task = {
            'id': str(int(time.time() * 1000)),
            'type': data.get('type'),  # launch_app, shutdown, reboot
            'scheduled_time': data.get('scheduled_time'),  # ISO format
            'app_path': data.get('app_path', ''),
            'recurring': data.get('recurring', False),
            'created_at': datetime.now().isoformat()
        }

        scheduled_tasks.append(task)
        save_scheduled_tasks()

        logger.info(f"Task scheduled: {task['type']} at {task['scheduled_time']}")
        return jsonify({"success": True, "task": task})
    except Exception as e:
        logger.error(f"Failed to add scheduled task: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/pc/scheduler/delete/<task_id>', methods=['DELETE'])
@rate_limit
@require_auth
def delete_scheduled_task(task_id):
    """Видалити заплановану задачу"""
    try:
        global scheduled_tasks
        scheduled_tasks = [t for t in scheduled_tasks if t.get('id') != task_id]
        save_scheduled_tasks()

        logger.info(f"Task deleted: {task_id}")
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Failed to delete scheduled task: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/pc/apps/favorites', methods=['GET'])
@rate_limit
def get_favorite_apps():
    """Отримати список улюблених програм"""
    favorites = [
        {"name": "Firefox", "path": "firefox", "icon": "🦊"},
        {"name": "VS Code", "path": "code", "icon": "💻"},
        {"name": "Terminal", "path": "ptyxis", "icon": "⌨️"},
        {"name": "Files", "path": "nautilus", "icon": "📁"},
        {"name": "Discord", "path": "discord", "icon": "💬"},
    ]
    return jsonify({"apps": favorites, "success": True})

@app.route('/api/pc/apps/launch', methods=['POST'])
@rate_limit
def launch_app():
    """Запустити програму"""
    try:
        data = request.json or {}
        app_path = data.get('path', '')

        if not app_path:
            return jsonify({"error": "No app path provided"}), 400

        env = get_gui_env()
        subprocess.Popen([app_path], env=env, start_new_session=True)

        logger.info(f"Launched app: {app_path}")
        return jsonify({"success": True, "app": app_path})
    except Exception as e:
        logger.error(f"Failed to launch app: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("Starting Flask API Server")
    logger.info(f"Database: {DB_PATH}")
    logger.info(f"Motion detection: {'enabled' if motion_enabled else 'disabled'}")
    logger.info(f"Rate limit: {RATE_LIMIT_MAX_REQUESTS} requests per {RATE_LIMIT_WINDOW}s")
    logger.info("=" * 60)

    # Завантажуємо заплановані задачі
    load_scheduled_tasks()

    # Запускаємо планувальник в окремому потоці
    scheduler_t = threading.Thread(target=scheduler_thread, daemon=True)
    scheduler_t.start()
    logger.info("Scheduler thread started")

    # Невелика затримка для повної ініціалізації
    time.sleep(1)
    logger.info("Flask server ready to accept connections")

    app.run(host='0.0.0.0', port=5000, threaded=True, debug=False)
