import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import threading
import time
import json
import os
import logging
from datetime import datetime
from pynput.mouse import Button, Controller
from pynput.keyboard import Listener, KeyCode

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('autoclicker.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AutoClicker:
    def __init__(self):
        try:
            self.mouse = Controller()
            self.running = False
            self.enabled = False
            self.delay = 0.1
            self.button = Button.left
            self.toggle_key = KeyCode(char='s')
            self.pause_key = KeyCode(char='p')
            self.click_count = 0
            self.total_clicks = 0
            self.session_start = time.time()
            self.on_toggle_callback = None
            self.profiles_dir = "config"
            self.stats_file = os.path.join(self.profiles_dir, "autoclicker_stats.json")
            self.max_clicks = None
            self.click_limit_enabled = False

            if not os.path.exists(self.profiles_dir):
                os.makedirs(self.profiles_dir)
                logger.info(f"Created config directory: {self.profiles_dir}")

            self.load_stats()
            logger.info("AutoClicker initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize AutoClicker: {e}")
            raise

        self.load_stats()

    def load_stats(self):
        """Завантажує статистику з файлу"""
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.total_clicks = data.get('total_clicks', 0)
                    logger.info(f"Loaded stats: {self.total_clicks} total clicks")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse stats file: {e}")
                self.total_clicks = 0
            except Exception as e:
                logger.error(f"Failed to load stats: {e}")
                self.total_clicks = 0
        else:
            self.total_clicks = 0

    def save_stats(self):
        """Зберігає статистику у файл"""
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'total_clicks': self.total_clicks,
                    'last_session': datetime.now().isoformat(),
                    'last_session_clicks': self.click_count
                }, f, indent=2)
            logger.info(f"Stats saved: {self.total_clicks} total clicks")
        except Exception as e:
            logger.error(f"Failed to save stats: {e}")

    def save_profile(self, name):
        """Зберігає поточний профіль"""
        if not name or len(name.strip()) == 0:
            logger.warning("Attempted to save profile with empty name")
            return False

        profile = {
            'delay': self.delay,
            'button': 'left' if self.button == Button.left else 'right',
            'created': datetime.now().isoformat(),
            'max_clicks': self.max_clicks,
            'click_limit_enabled': self.click_limit_enabled
        }
        profile_path = os.path.join(self.profiles_dir, f"{name}.json")
        try:
            with open(profile_path, 'w', encoding='utf-8') as f:
                json.dump(profile, f, indent=2)
            logger.info(f"Profile '{name}' saved successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to save profile '{name}': {e}")
            return False

    def load_profile(self, name):
        """Завантажує профіль"""
        profile_path = os.path.join(self.profiles_dir, f"{name}.json")
        if os.path.exists(profile_path):
            try:
                with open(profile_path, 'r', encoding='utf-8') as f:
                    profile = json.load(f)
                    self.delay = profile.get('delay', 0.1)
                    self.button = Button.left if profile.get('button') == 'left' else Button.right
                    self.max_clicks = profile.get('max_clicks')
                    self.click_limit_enabled = profile.get('click_limit_enabled', False)
                logger.info(f"Profile '{name}' loaded successfully")
                return True
            except Exception as e:
                logger.error(f"Failed to load profile '{name}': {e}")
        return False

    def get_profiles(self):
        """Повертає список доступних профілів"""
        if not os.path.exists(self.profiles_dir):
            return []
        return [f[:-5] for f in os.listdir(self.profiles_dir) if f.endswith('.json') and f != 'autoclicker_stats.json']  # Викликається при зміні стану

    def toggle_clicking(self):
        self.running = not self.running
        if not self.running:
            self.click_count = 0
            self.save_stats()
        if self.on_toggle_callback:
            self.on_toggle_callback(self.running)
        logger.info(f"Clicking {'started' if self.running else 'stopped'}")

    def run(self):
        logger.info("AutoClicker thread started")
        while self.enabled:
            if self.running:
                try:
                    if self.click_limit_enabled and self.max_clicks and self.click_count >= self.max_clicks:
                        logger.info(f"Click limit reached: {self.max_clicks}")
                        self.running = False
                        if self.on_toggle_callback:
                            self.on_toggle_callback(False)
                        continue

                    self.mouse.click(self.button)
                    self.click_count += 1
                    self.total_clicks += 1
                except Exception as e:
                    logger.error(f"Click error: {e}")
            time.sleep(self.delay)
        logger.info("AutoClicker thread stopped")


class App(tk.Tk):
    def __init__(self, clicker):
        super().__init__()
        self.clicker = clicker
        self.clicker.on_toggle_callback = self._on_toggle
        self.title("AutoClicker Pro v2.5")
        self.geometry("420x550")
        self.resizable(False, False)

        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill="both", expand=True)

        self.status_label = tk.Label(
            main_frame, text="⏹ ЗУПИНЕНО",
            foreground="red", font=("Arial", 14, "bold"),
        )
        self.status_label.pack(pady=10)

        stats_frame = ttk.LabelFrame(main_frame, text="📊 Статистика", padding="10")
        stats_frame.pack(fill="x", pady=10)

        self.count_label = ttk.Label(stats_frame, text=f"Поточна сесія: 0", font=("Arial", 10))
        self.count_label.pack()

        self.total_label = ttk.Label(stats_frame, text=f"Всього кліків: {clicker.total_clicks}", font=("Arial", 10))
        self.total_label.pack()

        self.time_label = ttk.Label(stats_frame, text="Час роботи: 0с", font=("Arial", 10))
        self.time_label.pack()

        self.cps_label = ttk.Label(stats_frame, text="CPS: 0.0", font=("Arial", 10))
        self.cps_label.pack()

        settings_frame = ttk.LabelFrame(main_frame, text="⚙️ Налаштування", padding="10")
        settings_frame.pack(fill="x", pady=10)

        ttk.Label(settings_frame, text="Інтервал кліку (сек):").pack()
        self.delay_entry = ttk.Entry(settings_frame)
        self.delay_entry.insert(0, "0.1")
        self.delay_entry.pack(pady=5, fill="x")

        ttk.Label(settings_frame, text="Кнопка миші:").pack()
        self.mouse_btn_var = tk.StringVar(value="Ліва")
        self.mouse_btn_combo = ttk.Combobox(
            settings_frame, textvariable=self.mouse_btn_var,
            values=["Ліва", "Права"], state="readonly",
        )
        self.mouse_btn_combo.pack(pady=5, fill="x")

        limit_frame = ttk.Frame(settings_frame)
        limit_frame.pack(fill="x", pady=5)

        self.limit_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(limit_frame, text="Обмеження кліків:", variable=self.limit_var).pack(side="left")
        self.limit_entry = ttk.Entry(limit_frame, width=10)
        self.limit_entry.insert(0, "100")
        self.limit_entry.pack(side="left", padx=5)

        ttk.Button(settings_frame, text="✅ Застосувати", command=self.apply).pack(pady=5)

        profiles_frame = ttk.LabelFrame(main_frame, text="💾 Профілі", padding="10")
        profiles_frame.pack(fill="x", pady=10)

        profile_buttons = ttk.Frame(profiles_frame)
        profile_buttons.pack(fill="x")

        ttk.Button(profile_buttons, text="💾 Зберегти", command=self.save_profile).pack(side="left", expand=True, padx=2)
        ttk.Button(profile_buttons, text="📂 Завантажити", command=self.load_profile).pack(side="left", expand=True, padx=2)
        ttk.Button(profile_buttons, text="🗑️ Видалити", command=self.delete_profile).pack(side="left", expand=True, padx=2)

        ttk.Label(
            main_frame, text="⌨️ Гарячі клавіші:\n[ S ] - Старт/Стоп\n[ P ] - Пауза",
            foreground="gray", font=("Arial", 9), justify="center"
        ).pack(pady=10)

        self._update_counter()

    def delete_profile(self):
        """Видаляє профіль"""
        profiles = self.clicker.get_profiles()
        if not profiles:
            messagebox.showinfo("Інфо", "Немає збережених профілів")
            return

        dialog = tk.Toplevel(self)
        dialog.title("Видалити профіль")
        dialog.geometry("300x200")

        ttk.Label(dialog, text="Оберіть профіль для видалення:").pack(pady=10)

        listbox = tk.Listbox(dialog)
        listbox.pack(fill="both", expand=True, padx=10)

        for profile in profiles:
            listbox.insert(tk.END, profile)

        def delete_selected():
            selection = listbox.curselection()
            if selection:
                profile_name = listbox.get(selection[0])
                if messagebox.askyesno("Підтвердження", f"Видалити профіль '{profile_name}'?"):
                    try:
                        profile_path = os.path.join(self.clicker.profiles_dir, f"{profile_name}.json")
                        os.remove(profile_path)
                        messagebox.showinfo("Успіх", f"Профіль '{profile_name}' видалено!")
                        dialog.destroy()
                    except Exception as e:
                        messagebox.showerror("Помилка", f"Не вдалося видалити профіль: {e}")

        ttk.Button(dialog, text="Видалити", command=delete_selected).pack(pady=10)

    def save_profile(self):
        name = simpledialog.askstring("Зберегти профіль", "Введіть назву профілю:")
        if name:
            if self.clicker.save_profile(name):
                messagebox.showinfo("Успіх", f"Профіль '{name}' збережено!")
            else:
                messagebox.showerror("Помилка", "Не вдалося зберегти профіль")

    def load_profile(self):
        profiles = self.clicker.get_profiles()
        if not profiles:
            messagebox.showinfo("Інфо", "Немає збережених профілів")
            return

        dialog = tk.Toplevel(self)
        dialog.title("Завантажити профіль")
        dialog.geometry("300x200")

        ttk.Label(dialog, text="Оберіть профіль:").pack(pady=10)

        listbox = tk.Listbox(dialog)
        listbox.pack(fill="both", expand=True, padx=10)

        for profile in profiles:
            listbox.insert(tk.END, profile)

        def load_selected():
            selection = listbox.curselection()
            if selection:
                profile_name = listbox.get(selection[0])
                if self.clicker.load_profile(profile_name):
                    self.delay_entry.delete(0, "end")
                    self.delay_entry.insert(0, str(self.clicker.delay))
                    self.mouse_btn_var.set("Ліва" if self.clicker.button == Button.left else "Права")
                    messagebox.showinfo("Успіх", f"Профіль '{profile_name}' завантажено!")
                    dialog.destroy()
                else:
                    messagebox.showerror("Помилка", "Не вдалося завантажити профіль")

        ttk.Button(dialog, text="Завантажити", command=load_selected).pack(pady=10)

    def _on_toggle(self, is_running: bool):
        """Викликається з потоку клавіатури — планує оновлення UI через after()"""
        self.after(0, self._refresh_status, is_running)

    def _refresh_status(self, is_running: bool):
        if is_running:
            self.status_label.config(text="▶ ПРАЦЮЄ", foreground="green")
        else:
            self.status_label.config(text="⏹ ЗУПИНЕНО", foreground="red")

    def _update_counter(self):
        self.count_label.config(text=f"Поточна сесія: {self.clicker.click_count}")
        self.total_label.config(text=f"Всього кліків: {self.clicker.total_clicks}")

        if self.clicker.running:
            elapsed = int(time.time() - self.clicker.session_start)
            self.time_label.config(text=f"Час роботи: {elapsed}с")

            if elapsed > 0:
                cps = self.clicker.click_count / elapsed
                self.cps_label.config(text=f"CPS: {cps:.2f}")

        self.after(200, self._update_counter)

    def apply(self):
        try:
            val = float(self.delay_entry.get())
            if val <= 0:
                raise ValueError("Delay must be positive")
            self.clicker.delay = val
            self.clicker.button = (
                Button.left if self.mouse_btn_var.get() == "Ліва" else Button.right
            )

            self.clicker.click_limit_enabled = self.limit_var.get()
            if self.clicker.click_limit_enabled:
                try:
                    self.clicker.max_clicks = int(self.limit_entry.get())
                except ValueError:
                    messagebox.showerror("Помилка", "Невірне значення обмеження кліків")
                    return

            messagebox.showinfo("Успіх", "Налаштування застосовано!")
            logger.info(f"Settings applied: delay={val}, button={self.mouse_btn_var.get()}, limit={self.clicker.max_clicks if self.clicker.click_limit_enabled else 'None'}")
        except ValueError as e:
            messagebox.showerror("Помилка", "Невірне значення інтервалу")
            self.delay_entry.delete(0, "end")
            self.delay_entry.insert(0, str(self.clicker.delay))


def start_logic(clicker):
    clicker.enabled = True
    clicker.run()


if __name__ == "__main__":
    try:
        logger.info("=" * 60)
        logger.info("Starting AutoClicker Pro v2.5")
        logger.info("=" * 60)

        clicker = AutoClicker()

        t = threading.Thread(target=clicker.run, daemon=True)
        t.start()

        def on_press(key):
            try:
                if key == clicker.toggle_key:
                    if not clicker.running:
                        clicker.session_start = time.time()
                    clicker.toggle_clicking()
                elif key == clicker.pause_key:
                    clicker.running = False
                    if clicker.on_toggle_callback:
                        clicker.on_toggle_callback(False)
            except Exception as e:
                logger.error(f"Key press error: {e}")

        listener = Listener(on_press=on_press)
        listener.start()

        app = App(clicker)
        app.mainloop()

        clicker.enabled = False
        clicker.save_stats()
        logger.info("AutoClicker stopped gracefully")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise
