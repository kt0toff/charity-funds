# 🪟 Інструкція для Windows

## 📋 Що потрібно перенести

Скопіюйте ці файли на Windows комп'ютер:

```
charity_server.py          - Серверна частина
charity_funds.html         - Веб-інтерфейс
charity_funds.db          - База даних (якщо вже є дані)
start_charity_windows.bat - Скрипт запуску для Windows
```

## 🔧 Підготовка Windows

### 1. Встановіть Python
- Завантажте з https://www.python.org/downloads/
- **ВАЖЛИВО**: При встановленні поставте галочку "Add Python to PATH"
- Версія: Python 3.8 або новіша

### 2. Встановіть необхідні бібліотеки
Відкрийте командний рядок (cmd) і виконайте:
```cmd
pip install flask flask-cors
```

## 🚀 Запуск на Windows

### Варіант 1: Через BAT файл (найпростіше)
1. Подвійний клік на `start_charity_windows.bat`
2. Відкриється вікно з сервером
3. Відкрийте браузер: http://localhost:5001

### Варіант 2: Через командний рядок
1. Відкрийте cmd у папці з файлами
2. Виконайте:
```cmd
python charity_server.py
```
3. Відкрийте браузер: http://localhost:5001

## 📁 Структура папки на Windows

```
C:\charity\
├── charity_server.py
├── charity_funds.html
├── charity_funds.db
└── start_charity_windows.bat
```

## 💾 База даних

### Перенесення існуючих даних
Якщо у вас вже є дані на Linux:
1. Скопіюйте файл `charity_funds.db` з Linux
2. Помістіть його в ту саму папку на Windows
3. Всі дані автоматично будуть доступні!

### Нова база даних
Якщо файлу `charity_funds.db` немає:
- Він створиться автоматично при першому запуску
- Буде містити приклади даних

## 🌐 Доступ з інших пристроїв

### У локальній мережі
1. Дізнайтеся IP адресу Windows комп'ютера:
```cmd
ipconfig
```
Шукайте "IPv4 Address", наприклад: `192.168.1.100`

2. На іншому пристрої відкрийте:
```
http://192.168.1.100:5001
```

### Через інтернет (ngrok)
1. Завантажте ngrok: https://ngrok.com/download
2. Розпакуйте ngrok.exe у папку з проєктом
3. Створіть файл `start_charity_public_windows.bat`:

```batch
@echo off
echo Запуск сервера...
start /B python charity_server.py

timeout /t 3 /nobreak >nul

echo Створення публічного посилання...
ngrok http 5001
```

4. Запустіть `start_charity_public_windows.bat`
5. Скопіюйте посилання з вікна ngrok (наприклад: https://abc123.ngrok.io)

## ⚠️ Важливо для Windows

### Брандмауер Windows
При першому запуску Windows може запитати дозвіл:
- ✅ Натисніть "Дозволити доступ"
- Це потрібно щоб інші пристрої могли підключитися

### Антивірус
Якщо антивірус блокує:
- Додайте папку проєкту в виключення
- Або дозвольте `python.exe`

### Автозапуск при старті Windows
1. Натисніть `Win + R`
2. Введіть: `shell:startup`
3. Скопіюйте туди ярлик на `start_charity_windows.bat`

## 🔄 Оновлення

Щоб оновити сайт:
1. Замініть файли `charity_server.py` та `charity_funds.html`
2. **НЕ ЗАМІНЮЙТЕ** `charity_funds.db` (там ваші дані!)
3. Перезапустіть сервер

## 💾 Резервне копіювання

### Ручне
Просто скопіюйте файл `charity_funds.db` в безпечне місце

### Автоматичне (через Task Scheduler)
1. Створіть файл `backup_charity_windows.bat`:
```batch
@echo off
set BACKUP_DIR=C:\charity\backups
set DATE=%date:~-4%%date:~3,2%%date:~0,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set DATE=%DATE: =0%

if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"
copy charity_funds.db "%BACKUP_DIR%\charity_backup_%DATE%.db"
echo Backup created: %DATE%
```

2. Налаштуйте Task Scheduler для щоденного запуску

## 🆘 Вирішення проблем

### Помилка "Python не знайдено"
- Переконайтеся що Python встановлено
- Перевірте що Python додано в PATH
- Перезавантажте комп'ютер після встановлення

### Помилка "Port 5001 is already in use"
- Закрийте інші програми що використовують порт 5001
- Або змініть порт в `charity_server.py` (рядок: `app.run(..., port=5001)`)

### Сайт не відкривається
- Перевірте що сервер запущено (вікно cmd має бути відкрите)
- Перевірте брандмауер Windows
- Спробуйте http://127.0.0.1:5001 замість localhost

### База даних не зберігає зміни
- Перевірте права доступу до папки
- Запускайте від імені адміністратора

## 📞 Контакти

Якщо виникли питання - перевірте логи у вікні командного рядка.

---

**Успіхів! 🤝💙💛**
