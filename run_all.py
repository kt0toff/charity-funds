import subprocess
import time
import sys
import os
import socket
import logging
from datetime import datetime
from pyngrok import ngrok

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('run_all.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

FLASK_PORT = 5000
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, ".env")
MAX_RESTART_ATTEMPTS = 3
RESTART_COOLDOWN = 30

def check_internet():
    """Перевіряє доступ до інтернету"""
    try:
        socket.setdefaulttimeout(3)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
        return True
    except socket.error as e:
        logger.warning(f"Internet check failed: {e}")
        return False

def wait_for_flask(port, timeout=30):
    """Чекає поки Flask сервер стане доступним"""
    logger.info(f"Waiting for Flask server on port {port}...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()

            if result == 0:
                # Порт відкритий, перевіряємо чи Flask відповідає
                try:
                    response = subprocess.run(
                        ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                         f"http://127.0.0.1:{port}/api/pc/status"],
                        capture_output=True,
                        timeout=2
                    )
                    if response.returncode == 0:
                        logger.info(f"✅ Flask server is ready on port {port}")
                        return True
                except:
                    pass
        except:
            pass

        time.sleep(0.5)

    logger.warning(f"Flask server did not become ready within {timeout}s")
    return False

def kill_everything():
    """Повне очищення всіх процесів перед стартом або при перезапуску"""
    logger.info("Cleaning up old processes...")
    subprocess.run(["fuser", "-k", "-9", f"{FLASK_PORT}/tcp"], capture_output=True)
    subprocess.run(["pkill", "-9", "ngrok"], capture_output=True)

    scripts_to_kill = ["app.py", "telegram_bot_couples.py", "remote_bot.py"]
    for script in scripts_to_kill:
        result = subprocess.run(["pkill", "-9", "-f", script], capture_output=True)
        if result.returncode == 0:
            logger.info(f"Killed process: {script}")

    time.sleep(1)

def update_env(key, value):
    """Оновлює .env файл"""
    lines = []
    if os.path.exists(ENV_FILE):
        try:
            with open(ENV_FILE, "r") as f:
                lines = f.readlines()
        except Exception as e:
            logger.error(f"Failed to read .env file: {e}")
            return False

    found = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}\n"
            found = True
            break

    if not found:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        lines.append(f"{key}={value}\n")

    try:
        with open(ENV_FILE, "w") as f:
            f.writelines(lines)
        logger.info(f"Updated .env: {key}={value[:50]}...")
        return True
    except Exception as e:
        logger.error(f"Failed to write .env file: {e}")
        return False

def run_ngrok(port):
    """Запуск ngrok з повним очищенням"""
    logger.info(f"Starting ngrok on port {port}...")
    try:
        ngrok.kill()
        time.sleep(2)
        public_url = ngrok.connect(port).public_url
        update_env("WEB_APP_URL", public_url)
        logger.info(f"✅ NGROK ACTIVE: {public_url}")
        return public_url
    except Exception as e:
        logger.error(f"Ngrok failed: {e}")
        subprocess.run(["pkill", "-9", "ngrok"], capture_output=True)
        return None

def start_service(name, command):
    """Запуск сервісу з логуванням"""
    logger.info(f"Starting service: {name}")
    try:
        process = subprocess.Popen(
            [sys.executable] + command,
            cwd=BASE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        logger.info(f"✅ {name} started (PID: {process.pid})")
        return process
    except Exception as e:
        logger.error(f"Failed to start {name}: {e}")
        return None

def check_process_health(name, process):
    """Перевіряє здоров'я процесу"""
    if process is None:
        return False
    return process.poll() is None

if __name__ == "__main__":
    processes = {}
    last_internet_status = True
    current_ngrok_url = None
    restart_attempts = {}

    kill_everything()

    logger.info("=" * 60)
    logger.info("Bot Management System Started")
    logger.info(f"Base directory: {BASE_DIR}")
    logger.info(f"Flask port: {FLASK_PORT}")
    logger.info("=" * 60)

    try:
        while True:
            internet = check_internet()

            if internet:
                if not last_internet_status:
                    logger.info("Internet restored! Reconnecting tunnel...")
                    current_ngrok_url = None

                if current_ngrok_url is None:
                    for name in ["Couple Бот", "PC Control Бот"]:
                        if name in processes:
                            logger.info(f"Stopping {name} before URL update...")
                            try:
                                processes[name].terminate()
                                processes[name].wait(timeout=3)
                            except subprocess.TimeoutExpired:
                                processes[name].kill()
                            except Exception as e:
                                logger.error(f"Error stopping {name}: {e}")
                            del processes[name]

                    current_ngrok_url = run_ngrok(FLASK_PORT)
                    if not current_ngrok_url:
                        logger.warning("Failed to start ngrok, retrying in 5s...")
                        time.sleep(5)
                        continue
                    update_env("WEB_APP_URL", current_ngrok_url)

                if "API Сервер" not in processes or not check_process_health("API Сервер", processes.get("API Сервер")):
                    if "API Сервер" in processes:
                        logger.warning("API Server died, restarting...")
                    processes["API Сервер"] = start_service("API Сервер", ["app.py"])

                    # Чекаємо поки Flask стане готовим перед запуском ботів
                    if not wait_for_flask(FLASK_PORT):
                        logger.error("Flask server failed to start properly")
                        continue

                if current_ngrok_url:
                    if "Couple Бот" not in processes or not check_process_health("Couple Бот", processes.get("Couple Бот")):
                        if "Couple Бот" in processes:
                            logger.warning("Couple Bot died, restarting...")
                        # Додаткова затримка перед запуском бота
                        time.sleep(2)
                        processes["Couple Бот"] = start_service("Couple Бот", ["telegram_bot_couples.py"])

                    if "PC Control Бот" not in processes or not check_process_health("PC Control Бот", processes.get("PC Control Бот")):
                        if "PC Control Бот" in processes:
                            logger.warning("PC Control Bot died, restarting...")
                        # Додаткова затримка перед запуском бота
                        time.sleep(2)
                        processes["PC Control Бот"] = start_service("PC Control Бот", ["pc_remote_control/remote_bot.py"])

            else:
                if last_internet_status:
                    logger.warning("Internet connection lost. Waiting...")
                current_ngrok_url = None

            last_internet_status = internet
            time.sleep(15)

    except KeyboardInterrupt:
        logger.info("\nShutting down system...")
        for name, proc in processes.items():
            logger.info(f"Stopping {name}...")
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
            except Exception as e:
                logger.error(f"Error stopping {name}: {e}")
        subprocess.run(["pkill", "-9", "ngrok"], capture_output=True)
        logger.info("All services stopped. Goodbye!")
    except Exception as e:
        logger.error(f"Fatal error in main loop: {e}", exc_info=True)
        raise
