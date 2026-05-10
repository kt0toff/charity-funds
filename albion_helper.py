import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import random
import sys
import os
import json
import logging
import traceback
from pynput.keyboard import Key, Controller as KController, Listener, KeyCode
from pynput.mouse import Button, Controller as MController
import pyautogui
import cv2
import numpy as np
from PIL import ImageGrab

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler("albion_helper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def log_message(msg):
    """Додаткове логування у файл для зворотної сумісності"""
    logger.info(msg)
    try:
        with open("albion_internal_error.log", "a") as f:
            f.write(f"[{time.ctime()}] {msg}\n")
    except Exception as e:
        logger.error(f"Failed to write to internal log: {e}")

log_message("Скрипт запускається...")

# Профілі для різних класів/зброї
WEAPON_PROFILES = {
    "Warrior (Axe)": {
        "combo": ['q', 'w', 'e', 'r'],
        "delays": [0.05, 0.15, 0.15, 0.2],
        "description": "Комбо для воїна з сокирою"
    },
    "Mage (Fire)": {
        "combo": ['q', 'w', 'e'],
        "delays": [0.1, 0.2, 0.3],
        "description": "Вогняне комбо мага"
    },
    "Healer": {
        "combo": ['q', 'w', 'e'],
        "delays": [0.05, 0.1, 0.15],
        "description": "Лікувальне комбо"
    },
    "Archer": {
        "combo": ['q', 'e', 'w'],
        "delays": [0.1, 0.15, 0.2],
        "description": "Комбо лучника"
    },
    "Tank": {
        "combo": ['q', 'w', 'e', 'r', 'f'],
        "delays": [0.1, 0.1, 0.15, 0.2, 0.1],
        "description": "Захисне комбо танка"
    },
    "Assassin": {
        "combo": ['e', 'q', 'w', 'r'],
        "delays": [0.05, 0.1, 0.1, 0.15],
        "description": "Швидке комбо асасина"
    },
    "Frost Mage": {
        "combo": ['q', 'w', 'e', 'r'],
        "delays": [0.15, 0.2, 0.25, 0.3],
        "description": "Крижане комбо мага"
    }
}

CONFIG_FILE = "albion_config.json"

# Кольори ресурсів в Albion (HSV діапазони для кращої детекції)
RESOURCE_COLORS = {
    "wood": {
        "lower": np.array([35, 40, 40]),
        "upper": np.array([85, 255, 255]),
        "min_area": 500
    },
    "stone": {
        "lower": np.array([0, 0, 80]),
        "upper": np.array([180, 50, 200]),
        "min_area": 600
    },
    "ore": {
        "lower": np.array([10, 100, 80]),
        "upper": np.array([25, 255, 200]),
        "min_area": 500
    },
    "fiber": {
        "lower": np.array([90, 50, 100]),
        "upper": np.array([130, 255, 255]),
        "min_area": 400
    },
    "hide": {
        "lower": np.array([15, 30, 150]),
        "upper": np.array([35, 150, 255]),
        "min_area": 450
    }
}

class AutoGatherBot:
    """Автоматичний бот для збору ресурсів"""
    def __init__(self, helper):
        self.helper = helper
        self.active = False
        self.resource_type = "wood"
        self.patrol_enabled = True
        self.safe_zone_return = True
        self.hp_threshold = 30

        self.screen_width = pyautogui.size()[0]
        self.screen_height = pyautogui.size()[1]
        self.scan_radius = 300
        self.center_x = self.screen_width // 2
        self.center_y = self.screen_height // 2

        self.resources_gathered = 0
        self.deaths_avoided = 0
        self.last_resource_pos = None
        self.stuck_counter = 0
        self.last_position = None

        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0.1

        logger.info(f"AutoGatherBot initialized - Screen: {self.screen_width}x{self.screen_height}")

    def find_resources_on_screen(self):
        """Шукає всі ресурси на екрані за кольором (покращена версія)"""
        try:
            screenshot = ImageGrab.grab()
            screen = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            hsv = cv2.cvtColor(screen, cv2.COLOR_BGR2HSV)

            resource_config = RESOURCE_COLORS.get(self.resource_type)
            if not resource_config:
                return []

            mask = cv2.inRange(hsv, resource_config['lower'], resource_config['upper'])

            kernel = np.ones((5, 5), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            resources = []
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > resource_config['min_area']:
                    M = cv2.moments(contour)
                    if M["m00"] > 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])

                        distance = ((cx - self.center_x)**2 + (cy - self.center_y)**2)**0.5

                        if distance < 600:
                            resources.append({
                                'pos': (cx, cy),
                                'distance': distance,
                                'area': area
                            })

            resources.sort(key=lambda x: x['distance'])
            return resources

        except Exception as e:
            logger.error(f"Resource detection error: {e}")
            return []

    def check_hp(self):
        """Перевіряє HP персонажа (покращена версія)"""
        try:
            hp_bar_region = (10, 10, 300, 100)
            screenshot = ImageGrab.grab(bbox=hp_bar_region)
            screen = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            hsv = cv2.cvtColor(screen, cv2.COLOR_BGR2HSV)

            red_lower = np.array([0, 100, 100])
            red_upper = np.array([10, 255, 255])
            mask1 = cv2.inRange(hsv, red_lower, red_upper)

            red_lower2 = np.array([170, 100, 100])
            red_upper2 = np.array([180, 255, 255])
            mask2 = cv2.inRange(hsv, red_lower2, red_upper2)

            mask = mask1 + mask2

            red_pixels = cv2.countNonZero(mask)
            total_pixels = mask.size
            hp_percent = (red_pixels / total_pixels) * 100

            return max(0, min(100, hp_percent))
        except Exception as e:
            logger.error(f"HP check error: {e}")
            return 100

    def move_to_position(self, x, y, click_type='right'):
        """Рухається до вказаної позиції (виправлена версія без слідування за мишкою)"""
        try:
            current_mouse_x, current_mouse_y = pyautogui.position()

            pyautogui.moveTo(x, y, duration=0.2)
            time.sleep(0.05)

            if click_type == 'right':
                pyautogui.click(x, y, button='right')
            else:
                pyautogui.click(x, y, button='left')

            time.sleep(0.1)

            pyautogui.moveTo(self.center_x, self.center_y, duration=0.1)

            distance = ((x - self.center_x)**2 + (y - self.center_y)**2)**0.5
            wait_time = min(distance / 300, 2.5)
            time.sleep(wait_time)

            logger.info(f"Moved to: ({x}, {y}), wait: {wait_time:.2f}s")
            return True
        except Exception as e:
            logger.error(f"Movement error: {e}")
            return False

    def gather_resource(self, x, y):
        """Збирає ресурс за координатами"""
        try:
            pyautogui.moveTo(x, y, duration=0.15)
            time.sleep(0.05)
            pyautogui.click(x, y, button='left')
            time.sleep(0.1)
            pyautogui.moveTo(self.center_x, self.center_y, duration=0.1)

            logger.info(f"Started gathering at ({x}, {y})")

            gather_time = random.uniform(3.0, 5.0)
            time.sleep(gather_time)

            self.resources_gathered += 1
            self.stuck_counter = 0
            logger.info(f"Resource gathered! Total: {self.resources_gathered}")
            return True
        except Exception as e:
            logger.error(f"Gathering error: {e}")
            return False

    def check_if_stuck(self):
        """Перевіряє чи застряг персонаж"""
        self.stuck_counter += 1
        if self.stuck_counter > 5:
            logger.warning("Character seems stuck, trying to unstuck...")
            self.unstuck()
            self.stuck_counter = 0

    def unstuck(self):
        """Виводить персонажа з застрягання"""
        try:
            angles = [0, 90, 180, 270]
            angle = random.choice(angles)

            offset_x = int(150 * np.cos(np.radians(angle)))
            offset_y = int(150 * np.sin(np.radians(angle)))

            target_x = self.center_x + offset_x
            target_y = self.center_y + offset_y

            self.move_to_position(target_x, target_y)
            logger.info("Unstuck maneuver completed")
        except Exception as e:
            logger.error(f"Unstuck error: {e}")

    def return_to_safe_zone(self):
        """Повертається до безпечної зони"""
        try:
            logger.warning("Low HP detected! Returning to safe zone...")

            self.helper.keyboard.press('m')
            time.sleep(0.3)
            self.helper.keyboard.release('m')
            time.sleep(1.5)

            safe_x = self.center_x - 150
            safe_y = self.center_y - 150

            pyautogui.moveTo(safe_x, safe_y, duration=0.2)
            time.sleep(0.1)
            pyautogui.click(safe_x, safe_y, button='right')
            time.sleep(0.2)
            pyautogui.moveTo(self.center_x, self.center_y, duration=0.1)

            time.sleep(6.0)

            self.helper.keyboard.press('m')
            time.sleep(0.3)
            self.helper.keyboard.release('m')

            self.deaths_avoided += 1
            logger.info(f"Returned to safe zone. Deaths avoided: {self.deaths_avoided}")

            time.sleep(3.0)
        except Exception as e:
            logger.error(f"Safe zone return error: {e}")

    def patrol_area(self):
        """Патрулює територію в пошуках ресурсів (покращена версія)"""
        try:
            angle = random.uniform(0, 2 * np.pi)
            radius = random.uniform(150, self.scan_radius)

            target_x = int(self.center_x + radius * np.cos(angle))
            target_y = int(self.center_y + radius * np.sin(angle))

            target_x = max(100, min(self.screen_width - 100, target_x))
            target_y = max(100, min(self.screen_height - 100, target_y))

            self.move_to_position(target_x, target_y)
            logger.info(f"Patrolling to ({target_x}, {target_y})")
        except Exception as e:
            logger.error(f"Patrol error: {e}")

    def run(self):
        """Основний цикл автоматичного бота (покращена версія)"""
        logger.info("AutoGatherBot started - Full autonomous mode")

        time.sleep(2.0)

        while self.active:
            try:
                if self.safe_zone_return:
                    hp = self.check_hp()
                    if hp < self.hp_threshold:
                        self.return_to_safe_zone()
                        continue

                resources = self.find_resources_on_screen()

                if resources:
                    logger.info(f"Found {len(resources)} resources on screen")

                    best_resource = resources[0]
                    res_x, res_y = best_resource['pos']

                    logger.info(f"Targeting resource at ({res_x}, {res_y}), distance: {best_resource['distance']:.1f}")

                    if best_resource['distance'] > 100:
                        self.move_to_position(res_x, res_y)
                        time.sleep(0.5)

                    self.gather_resource(res_x, res_y)

                    self.last_resource_pos = (res_x, res_y)
                else:
                    logger.info("No resources found")
                    self.check_if_stuck()

                    if self.patrol_enabled:
                        self.patrol_area()
                    else:
                        time.sleep(1.0)

                time.sleep(random.uniform(0.3, 0.8))

            except Exception as e:
                logger.error(f"Bot loop error: {e}")
                time.sleep(2.0)

        logger.info("AutoGatherBot stopped")

    def toggle(self):
        """Вмикає/вимикає бота"""
        self.active = not self.active
        if self.active:
            self.stuck_counter = 0
            self.last_resource_pos = None
        return self.active

    def get_stats(self):
        """Повертає статистику бота"""
        return {
            'active': self.active,
            'resource_type': self.resource_type,
            'resources_gathered': self.resources_gathered,
            'deaths_avoided': self.deaths_avoided
        }

class AlbionHelper:
    def __init__(self):
        try:
            self.keyboard = KController()
            self.mouse = MController()
            self.gathering_active = False
            self.enabled = True

            self.toggle_gather_key = KeyCode(char='f')
            self.combat_combo_key = KeyCode(char='v')
            self.profile_key = KeyCode(char='b')
            self.toggle_bot_key = KeyCode(char='g')

            self.current_profile = "Warrior (Axe)"
            self.custom_combo = None
            self.custom_delays = None

            self.gathering_min_delay = 1.5
            self.gathering_max_delay = 2.5
            self.combo_count = 0
            self.gathering_count = 0

            self.auto_bot = AutoGatherBot(self)

            self.load_config()
            log_message("Контролери ініціалізовані")
            logger.info(f"Current profile: {self.current_profile}")
        except Exception as e:
            log_message(f"Помилка ініціалізації AlbionHelper: {e}")
            logger.error(f"Initialization failed: {e}", exc_info=True)
            raise

    def load_config(self):
        """Завантажує конфігурацію з файлу"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.current_profile = config.get('profile', self.current_profile)
                    self.gathering_min_delay = config.get('gathering_min_delay', 1.5)
                    self.gathering_max_delay = config.get('gathering_max_delay', 2.5)
                    logger.info(f"Config loaded: profile={self.current_profile}")
            except Exception as e:
                logger.error(f"Failed to load config: {e}")

    def save_config(self):
        """Зберігає конфігурацію у файл"""
        try:
            config = {
                'profile': self.current_profile,
                'gathering_min_delay': self.gathering_min_delay,
                'gathering_max_delay': self.gathering_max_delay,
                'combo_count': self.combo_count,
                'gathering_count': self.gathering_count
            }
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            logger.info("Config saved successfully")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    def set_profile(self, profile_name):
        """Встановлює профіль зброї"""
        if profile_name in WEAPON_PROFILES:
            self.current_profile = profile_name
            log_message(f"Профіль змінено на: {profile_name}")
            self.save_config()
            return True
        logger.warning(f"Unknown profile: {profile_name}")
        return False

    def set_custom_combo(self, skills, delays):
        """Встановлює кастомне комбо"""
        if not skills or not delays:
            logger.warning("Invalid custom combo parameters")
            return False
        self.custom_combo = skills
        self.custom_delays = delays
        log_message(f"Кастомне комбо встановлено: {skills}")
        return True

    def toggle_gathering(self):
        self.gathering_active = not self.gathering_active
        log_message(f"Збір: {'АКТИВНИЙ' if self.gathering_active else 'ВИМКНЕНИЙ'}")
        return self.gathering_active

    def run_gathering(self):
        logger.info("Gathering thread started")
        while self.enabled:
            if self.gathering_active:
                try:
                    self.mouse.click(Button.left)
                    time.sleep(random.uniform(0.05, 0.1))

                    self.gathering_count += 1

                    time.sleep(random.uniform(self.gathering_min_delay, self.gathering_max_delay))
                except Exception as e:
                    log_message(f"Помилка у циклі збору: {e}")
                    logger.error(f"Gathering error: {e}")
                    time.sleep(1)
            else:
                time.sleep(0.5)
        logger.info("Gathering thread stopped")

    def execute_combat_combo(self):
        """Виконує бойове комбо на основі поточного профілю"""
        try:
            if self.custom_combo:
                skills = self.custom_combo
                delays = self.custom_delays
            else:
                profile = WEAPON_PROFILES.get(self.current_profile)
                if not profile:
                    logger.error(f"Profile not found: {self.current_profile}")
                    return
                skills = profile['combo']
                delays = profile['delays']

            for i, skill in enumerate(skills):
                self.keyboard.press(skill)
                time.sleep(random.uniform(0.03, 0.07))
                self.keyboard.release(skill)
                if i < len(delays):
                    time.sleep(delays[i] + random.uniform(-0.02, 0.02))

            self.combo_count += 1
            log_message(f"Комбо виконано: {self.current_profile} (#{self.combo_count})")
            logger.info(f"Combo executed: {self.current_profile}")
        except Exception as e:
            log_message(f"Помилка у комбо: {e}")
            logger.error(f"Combo error: {e}", exc_info=True)

    def toggle_auto_bot(self):
        """Вмикає/вимикає автоматичного бота"""
        status = self.auto_bot.toggle()
        log_message(f"Авто-бот: {'АКТИВНИЙ' if status else 'ВИМКНЕНИЙ'}")
        return status

    def get_stats(self):
        """Повертає статистику використання"""
        bot_stats = self.auto_bot.get_stats()
        return {
            'profile': self.current_profile,
            'combo_count': self.combo_count,
            'gathering_count': self.gathering_count,
            'gathering_active': self.gathering_active,
            'bot_active': bot_stats['active'],
            'bot_resources': bot_stats['resources_gathered'],
            'bot_deaths_avoided': bot_stats['deaths_avoided']
        }

class App(tk.Tk):
    def __init__(self, helper):
        super().__init__()
        self.helper = helper
        self.title("Albion Auto-Gather Bot v3.0")
        self.geometry("450x700")
        self.attributes('-topmost', True)

        frame = ttk.Frame(self, padding="20")
        frame.pack(fill="both", expand=True)

        # Статус автоматичного бота
        bot_status_frame = ttk.LabelFrame(frame, text="🤖 Автоматичний бот", padding="10")
        bot_status_frame.pack(fill="x", pady=10)

        self.status_bot = tk.Label(bot_status_frame, text="БОТ: ВИМКНЕНО", fg="red", font=("Arial", 12, "bold"))
        self.status_bot.pack(pady=5)

        ttk.Button(bot_status_frame, text="Запустити бота", command=self.toggle_bot).pack(pady=5)

        # Налаштування бота
        bot_settings_frame = ttk.LabelFrame(frame, text="⚙️ Налаштування бота", padding="10")
        bot_settings_frame.pack(fill="x", pady=10)

        ttk.Label(bot_settings_frame, text="Тип ресурсу:").pack(anchor="w")
        self.resource_var = tk.StringVar(value="wood")
        resource_options = ["wood", "stone", "ore", "fiber", "hide"]
        for res in resource_options:
            ttk.Radiobutton(
                bot_settings_frame,
                text=res.capitalize(),
                variable=self.resource_var,
                value=res,
                command=self.change_resource
            ).pack(anchor="w")

        self.patrol_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            bot_settings_frame,
            text="Патрулювання території",
            variable=self.patrol_var,
            command=self.toggle_patrol
        ).pack(anchor="w", pady=5)

        self.safe_zone_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            bot_settings_frame,
            text="Повернення в безпечну зону при низькому HP",
            variable=self.safe_zone_var,
            command=self.toggle_safe_zone
        ).pack(anchor="w")

        # Статус ручного збору
        self.status_gather = tk.Label(frame, text="РУЧНИЙ ЗБІР: ВИМКНЕНО", fg="red", font=("Arial", 10, "bold"))
        self.status_gather.pack(pady=10)

        # Статистика
        stats_frame = ttk.LabelFrame(frame, text="📊 Статистика", padding="10")
        stats_frame.pack(fill="x", pady=10)

        self.bot_resources_label = ttk.Label(stats_frame, text="Бот зібрав: 0", font=("Arial", 10))
        self.bot_resources_label.pack()

        self.deaths_avoided_label = ttk.Label(stats_frame, text="Уникнуто смертей: 0", font=("Arial", 10))
        self.deaths_avoided_label.pack()

        self.combo_count_label = ttk.Label(stats_frame, text="Комбо виконано: 0", font=("Arial", 10))
        self.combo_count_label.pack()

        self.gather_count_label = ttk.Label(stats_frame, text="Ручний збір: 0", font=("Arial", 10))
        self.gather_count_label.pack()

        # Профіль зброї
        profile_frame = ttk.LabelFrame(frame, text="⚔️ Профіль зброї", padding="10")
        profile_frame.pack(fill="x", pady=10)

        self.profile_var = tk.StringVar(value=helper.current_profile)
        for profile_name in WEAPON_PROFILES.keys():
            ttk.Radiobutton(
                profile_frame,
                text=profile_name,
                variable=self.profile_var,
                value=profile_name,
                command=self.change_profile
            ).pack(anchor="w")

        self.combo_info = ttk.Label(frame, text="", font=("Arial", 9), foreground="gray", wraplength=400)
        self.combo_info.pack(pady=5)
        self.update_combo_info()

        # Гарячі клавіші
        hotkeys_frame = ttk.LabelFrame(frame, text="⌨️ Гарячі клавіші", padding="10")
        hotkeys_frame.pack(fill="x", pady=10)

        ttk.Label(hotkeys_frame, text="[ G ] - Увімкнути/Вимкнути Авто-бота").pack(anchor="w")
        ttk.Label(hotkeys_frame, text="[ F ] - Увімкнути/Вимкнути Ручний збір").pack(anchor="w")
        ttk.Label(hotkeys_frame, text="[ V ] - Виконати бойове комбо").pack(anchor="w")
        ttk.Label(hotkeys_frame, text="[ B ] - Швидка зміна профілю").pack(anchor="w")

        self.update_ui()
        self.update_stats()

    def toggle_bot(self):
        """Вмикає/вимикає автоматичного бота"""
        status = self.helper.toggle_auto_bot()
        if status:
            threading.Thread(target=self.helper.auto_bot.run, daemon=True).start()
            messagebox.showinfo("Бот запущено", "Автоматичний бот почав роботу!")
        else:
            messagebox.showinfo("Бот зупинено", "Автоматичний бот зупинено")

    def change_resource(self):
        """Змінює тип ресурсу для бота"""
        resource = self.resource_var.get()
        self.helper.auto_bot.resource_type = resource
        logger.info(f"Resource type changed to: {resource}")

    def toggle_patrol(self):
        """Вмикає/вимикає патрулювання"""
        self.helper.auto_bot.patrol_enabled = self.patrol_var.get()
        logger.info(f"Patrol: {self.patrol_var.get()}")

    def toggle_safe_zone(self):
        """Вмикає/вимикає повернення в безпечну зону"""
        self.helper.auto_bot.safe_zone_return = self.safe_zone_var.get()
        logger.info(f"Safe zone return: {self.safe_zone_var.get()}")

    def change_profile(self):
        """Змінює профіль зброї"""
        profile_name = self.profile_var.get()
        if self.helper.set_profile(profile_name):
            self.update_combo_info()
            messagebox.showinfo("Успіх", f"Профіль змінено на: {profile_name}")

    def update_combo_info(self):
        """Оновлює інформацію про поточне комбо"""
        profile = WEAPON_PROFILES.get(self.helper.current_profile)
        if profile:
            combo_str = " → ".join(profile['combo']).upper()
            self.combo_info.config(text=f"Комбо: {combo_str}\n{profile['description']}")

    def update_stats(self):
        """Оновлює статистику"""
        stats = self.helper.get_stats()
        self.bot_resources_label.config(text=f"Бот зібрав: {stats['bot_resources']}")
        self.deaths_avoided_label.config(text=f"Уникнуто смертей: {stats['bot_deaths_avoided']}")
        self.combo_count_label.config(text=f"Комбо виконано: {stats['combo_count']}")
        self.gather_count_label.config(text=f"Ручний збір: {stats['gathering_count']}")
        self.after(1000, self.update_stats)

    def update_ui(self):
        if self.helper.auto_bot.active:
            self.status_bot.config(text="БОТ: ПРАЦЮЄ", fg="green")
        else:
            self.status_bot.config(text="БОТ: ВИМКНЕНО", fg="red")

        if self.helper.gathering_active:
            self.status_gather.config(text="РУЧНИЙ ЗБІР: ПРАЦЮЄ", fg="green")
        else:
            self.status_gather.config(text="РУЧНИЙ ЗБІР: ВИМКНЕНО", fg="red")
        self.after(200, self.update_ui)

if __name__ == "__main__":
    helper = None
    try:
        logger.info("=" * 60)
        logger.info("Starting Albion One-Hand Helper v2.5")
        logger.info("=" * 60)

        helper = AlbionHelper()

        t = threading.Thread(target=helper.run_gathering, daemon=True)
        t.start()

        def on_press(key):
            try:
                if key == helper.toggle_gather_key:
                    helper.toggle_gathering()
                elif key == helper.combat_combo_key:
                    threading.Thread(target=helper.execute_combat_combo, daemon=True).start()
                elif key == helper.toggle_bot_key:
                    status = helper.toggle_auto_bot()
                    if status:
                        threading.Thread(target=helper.auto_bot.run, daemon=True).start()
            except Exception as e:
                log_message(f"Помилка лістенера: {e}")
                logger.error(f"Listener error: {e}")

        listener = Listener(on_press=on_press)
        listener.start()
        log_message("Лістенер запущений")

        log_message("Запуск GUI...")
        app = App(helper)
        app.mainloop()

        logger.info("Application closed by user")
    except Exception as e:
        log_message(f"Критична помилка при старті: {e}")
        log_message(traceback.format_exc())
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        if helper:
            helper.enabled = False
            helper.save_config()
        log_message("Скрипт завершив роботу")
        logger.info("Albion Helper stopped")
