import google.generativeai as genai
import sys
import os

# Отримуємо ключ зі змінних оточення
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("Помилка: Не знайдено GEMINI_API_KEY. Експортуй його перед запуском.")
    sys.exit(1)

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-pro')
prompt = " ".join(sys.argv[1:])

if prompt:
    response = model.generate_content(prompt)
    print(response.text)
else:
    print("Введи запит. Наприклад: python gemini.py привіт")
