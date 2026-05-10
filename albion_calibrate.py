#!/usr/bin/env python3
"""
Калібрування кольорів ресурсів для Albion Auto-Gather Bot

Використання:
1. Запусти скрипт: python albion_calibrate.py
2. Наведи мишку на ресурс в грі
3. Натисни SPACE щоб зафіксувати колір
4. Скрипт покаже HSV значення для налаштування
"""

import cv2
import numpy as np
from PIL import ImageGrab
import pyautogui
from pynput import keyboard
import time

class ColorCalibrator:
    def __init__(self):
        self.running = True
        self.capture = False

    def on_press(self, key):
        try:
            if key == keyboard.Key.space:
                self.capture = True
            elif key == keyboard.Key.esc:
                self.running = False
        except:
            pass

    def get_color_at_mouse(self):
        """Отримує колір пікселя під мишкою"""
        x, y = pyautogui.position()

        # Захоплюємо область 50x50 навколо курсору
        region = (x - 25, y - 25, x + 25, y + 25)
        screenshot = ImageGrab.grab(bbox=region)
        screen = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        hsv = cv2.cvtColor(screen, cv2.COLOR_BGR2HSV)

        # Отримуємо середній колір області
        avg_hsv = np.mean(hsv, axis=(0, 1)).astype(int)
        avg_bgr = np.mean(screen, axis=(0, 1)).astype(int)

        return avg_hsv, avg_bgr, (x, y)

    def run(self):
        print("=" * 60)
        print("Albion Resource Color Calibrator")
        print("=" * 60)
        print("\nІнструкції:")
        print("1. Наведи мишку на ресурс в грі")
        print("2. Натисни SPACE щоб зафіксувати колір")
        print("3. Натисни ESC для виходу")
        print("\nОчікування...")

        listener = keyboard.Listener(on_press=self.on_press)
        listener.start()

        while self.running:
            if self.capture:
                hsv, bgr, pos = self.get_color_at_mouse()

                print("\n" + "=" * 60)
                print(f"Позиція миші: ({pos[0]}, {pos[1]})")
                print(f"BGR: {bgr}")
                print(f"HSV: {hsv}")
                print("\nДля albion_helper.py використай:")
                print(f'"lower": np.array([{max(0, hsv[0]-10)}, {max(0, hsv[1]-50)}, {max(0, hsv[2]-50)}]),')
                print(f'"upper": np.array([{min(180, hsv[0]+10)}, {min(255, hsv[1]+50)}, {min(255, hsv[2]+50)}]),')
                print("=" * 60)

                self.capture = False
                time.sleep(0.5)

            time.sleep(0.1)

        print("\nКалібрування завершено!")
        listener.stop()

if __name__ == "__main__":
    calibrator = ColorCalibrator()
    calibrator.run()
