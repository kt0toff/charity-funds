# 🔧 Швидке виправлення помилки деплою

## Крок 1: Перевірте логи

1. Зайдіть на https://dashboard.render.com
2. Відкрийте `charity-funds`
3. Вкладка **"Logs"**
4. Прокрутіть до кінця і знайдіть червоні помилки

## Найчастіші помилки:

### Помилка 1: ModuleNotFoundError: No module named 'psycopg2'
**Рішення:** Перевірте що `requirements.txt` містить `psycopg2-binary==2.9.9`

### Помилка 2: relation "resources" does not exist
**Рішення:** База даних не ініціалізувалася. Перезапустіть сервіс.

### Помилка 3: could not connect to server
**Рішення:** `DATABASE_URL` не налаштовано або неправильний.

## Крок 2: Ручний деплой

Спробуйте ручний деплой:
1. На сторінці сервісу натисніть **"Manual Deploy"** → **"Deploy latest commit"**
2. Дочекайтеся завершення
3. Перевірте логи

## Крок 3: Якщо нічого не допомагає

Тимчасово видаліть PostgreSQL і використайте SQLite з Persistent Disk:

1. Видаліть `DATABASE_URL` з Environment Variables
2. В налаштуваннях сервісу додайте **Disk**:
   - Name: `charity-data`
   - Mount Path: `/opt/render/project/src/data`
   - Size: 1 GB (безкоштовно перші 1GB)

3. Змініть в коді:
   ```python
   DB_PATH = '/opt/render/project/src/data/charity_funds.db'
   ```

---

**Скопіюйте сюди останні 20 рядків з логів і я точно скажу що не так!**
