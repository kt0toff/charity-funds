#!/bin/bash

# Скрипт для автоматичного резервного копіювання charity бази даних

BACKUP_DIR="/home/mnems1s/Documents/bot/charity_backups"
DB_FILE="/home/mnems1s/Documents/bot/charity_funds.db"
DATE=$(date +%Y-%m-%d_%H-%M-%S)
BACKUP_FILE="$BACKUP_DIR/charity_backup_$DATE.db"

# Створюємо папку для бекапів якщо її немає
mkdir -p "$BACKUP_DIR"

# Копіюємо базу даних
if [ -f "$DB_FILE" ]; then
    cp "$DB_FILE" "$BACKUP_FILE"
    echo "✅ Резервна копія створена: $BACKUP_FILE"

    # Видаляємо старі бекапи (залишаємо тільки останні 30)
    ls -t "$BACKUP_DIR"/charity_backup_*.db | tail -n +31 | xargs -r rm
    echo "📦 Всього бекапів: $(ls -1 "$BACKUP_DIR"/charity_backup_*.db | wc -l)"
else
    echo "❌ База даних не знайдена: $DB_FILE"
    exit 1
fi
