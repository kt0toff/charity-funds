from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import os
import json

app = Flask(__name__)
CORS(app)

# Визначаємо тип бази даних
DATABASE_URL = os.environ.get('DATABASE_URL')
USE_POSTGRES = DATABASE_URL is not None

if USE_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    # Виправлення для Render (postgres:// -> postgresql://)
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
else:
    import sqlite3
    DB_PATH = 'charity_funds.db'

def get_db_connection():
    """Отримати з'єднання з базою даних"""
    if USE_POSTGRES:
        return psycopg2.connect(DATABASE_URL)
    else:
        return sqlite3.connect(DB_PATH)

def init_db():
    """Ініціалізація бази даних"""
    conn = get_db_connection()

    if USE_POSTGRES:
        c = conn.cursor()
        # PostgreSQL синтаксис
        c.execute('''CREATE TABLE IF NOT EXISTS resources (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT,
                        icon TEXT
                     )''')

        c.execute('''CREATE TABLE IF NOT EXISTS funds (
                        id SERIAL PRIMARY KEY,
                        resource_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        contact TEXT,
                        conditions TEXT,
                        FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE
                     )''')

        c.execute("SELECT COUNT(*) FROM resources")
        count = c.fetchone()[0]
    else:
        c = conn.cursor()
        # SQLite синтаксис
        c.execute('''CREATE TABLE IF NOT EXISTS resources (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT,
                        icon TEXT
                     )''')

        c.execute('''CREATE TABLE IF NOT EXISTS funds (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        resource_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        contact TEXT,
                        conditions TEXT,
                        FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE
                     )''')

        c.execute("SELECT COUNT(*) FROM resources")
        count = c.fetchone()[0]

    if count == 0:
        default_resources = [
            ('food', 'Продукти харчування', 'Продуктові набори, гарячі обіди', '🍲'),
            ('medicine', 'Медикаменти', 'Ліки, медичне обладнання', '💊'),
            ('clothes', 'Одяг та взуття', 'Одяг, взуття, постільна білизна', '👕'),
            ('hygiene', 'Засоби гігієни', 'Особиста гігієна, побутова хімія', '🧼'),
            ('education', 'Освіта', 'Навчальні матеріали, курси', '📚'),
            ('housing', 'Житло', 'Тимчасове житло, оренда', '🏠'),
            ('legal', 'Юридична допомога', 'Консультації, представництво', '⚖️'),
            ('psychological', 'Психологічна підтримка', 'Консультації психолога', '🧠'),
            ('financial', 'Фінансова допомога', 'Грошова допомога, субсидії', '💰')
        ]

        if USE_POSTGRES:
            c.executemany("INSERT INTO resources VALUES (%s, %s, %s, %s)", default_resources)
        else:
            c.executemany("INSERT INTO resources VALUES (?, ?, ?, ?)", default_resources)

        default_funds = [
            ('food', 'Червоний Хрест України', 'тел: 0-800-331-800, redcross.org.ua',
             'Для ВПО, малозабезпечених сімей. Потрібна довідка про статус ВПО або довідка про доходи.'),
            ('food', 'Карітас України', 'тел: (044) 235-65-05, caritas-ua.org',
             'Для сімей з дітьми, людей похилого віку. Реєстрація через місцеві відділення.'),
            ('medicine', 'Лікарі без кордонів', 'тел: (044) 585-52-66, msf.org.ua',
             'Безкоштовні медичні консультації та ліки. Для ВПО та малозабезпечених.'),
        ]

        if USE_POSTGRES:
            c.executemany("INSERT INTO funds (resource_id, name, contact, conditions) VALUES (%s, %s, %s, %s)", default_funds)
        else:
            c.executemany("INSERT INTO funds (resource_id, name, contact, conditions) VALUES (?, ?, ?, ?)", default_funds)

    conn.commit()
    conn.close()

@app.route('/')
def index():
    return send_file('charity_funds.html', mimetype='text/html')

@app.route('/api/resources', methods=['GET'])
def get_resources():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, name, description, icon FROM resources")

    if USE_POSTGRES:
        resources = [{'id': r[0], 'name': r[1], 'description': r[2], 'icon': r[3]} for r in c.fetchall()]
    else:
        resources = [{'id': r[0], 'name': r[1], 'description': r[2], 'icon': r[3]} for r in c.fetchall()]

    conn.close()
    return jsonify(resources)

@app.route('/api/resources', methods=['POST'])
def add_resource():
    data = request.json
    conn = get_db_connection()
    c = conn.cursor()
    try:
        if USE_POSTGRES:
            c.execute("INSERT INTO resources (id, name, description, icon) VALUES (%s, %s, %s, %s)",
                     (data['id'], data['name'], data['description'], data['icon']))
        else:
            c.execute("INSERT INTO resources (id, name, description, icon) VALUES (?, ?, ?, ?)",
                     (data['id'], data['name'], data['description'], data['icon']))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/resources/<resource_id>', methods=['PUT'])
def update_resource(resource_id):
    data = request.json
    conn = get_db_connection()
    c = conn.cursor()

    if USE_POSTGRES:
        c.execute("UPDATE resources SET name=%s, description=%s, icon=%s WHERE id=%s",
                 (data['name'], data['description'], data['icon'], resource_id))
    else:
        c.execute("UPDATE resources SET name=?, description=?, icon=? WHERE id=?",
                 (data['name'], data['description'], data['icon'], resource_id))

    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/resources/<resource_id>', methods=['DELETE'])
def delete_resource(resource_id):
    conn = get_db_connection()
    c = conn.cursor()

    if USE_POSTGRES:
        c.execute("DELETE FROM funds WHERE resource_id=%s", (resource_id,))
        c.execute("DELETE FROM resources WHERE id=%s", (resource_id,))
    else:
        c.execute("DELETE FROM funds WHERE resource_id=?", (resource_id,))
        c.execute("DELETE FROM resources WHERE id=?", (resource_id,))

    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/funds/<resource_id>', methods=['GET'])
def get_funds(resource_id):
    conn = get_db_connection()
    c = conn.cursor()

    if USE_POSTGRES:
        c.execute("SELECT id, name, contact, conditions FROM funds WHERE resource_id=%s", (resource_id,))
    else:
        c.execute("SELECT id, name, contact, conditions FROM funds WHERE resource_id=?", (resource_id,))

    funds = [{'id': f[0], 'name': f[1], 'contact': f[2], 'conditions': f[3]} for f in c.fetchall()]
    conn.close()
    return jsonify(funds)

@app.route('/api/funds', methods=['POST'])
def add_fund():
    data = request.json
    conn = get_db_connection()
    c = conn.cursor()

    if USE_POSTGRES:
        c.execute("INSERT INTO funds (resource_id, name, contact, conditions) VALUES (%s, %s, %s, %s) RETURNING id",
                 (data['resource_id'], data['name'], data['contact'], data['conditions']))
        fund_id = c.fetchone()[0]
    else:
        c.execute("INSERT INTO funds (resource_id, name, contact, conditions) VALUES (?, ?, ?, ?)",
                 (data['resource_id'], data['name'], data['contact'], data['conditions']))
        fund_id = c.lastrowid

    conn.commit()
    conn.close()
    return jsonify({'success': True, 'id': fund_id})

@app.route('/api/funds/<int:fund_id>', methods=['PUT'])
def update_fund(fund_id):
    data = request.json
    conn = get_db_connection()
    c = conn.cursor()

    if USE_POSTGRES:
        c.execute("UPDATE funds SET name=%s, contact=%s, conditions=%s WHERE id=%s",
                 (data['name'], data['contact'], data['conditions'], fund_id))
    else:
        c.execute("UPDATE funds SET name=?, contact=?, conditions=? WHERE id=?",
                 (data['name'], data['contact'], data['conditions'], fund_id))

    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/funds/<int:fund_id>', methods=['DELETE'])
def delete_fund(fund_id):
    conn = get_db_connection()
    c = conn.cursor()

    if USE_POSTGRES:
        c.execute("DELETE FROM funds WHERE id=%s", (fund_id,))
    else:
        c.execute("DELETE FROM funds WHERE id=?", (fund_id,))

    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/export', methods=['GET'])
def export_data():
    conn = get_db_connection()
    c = conn.cursor()

    c.execute("SELECT id, name, description, icon FROM resources")
    resources = [{'id': r[0], 'name': r[1], 'description': r[2], 'icon': r[3]} for r in c.fetchall()]

    funds_dict = {}
    for resource in resources:
        if USE_POSTGRES:
            c.execute("SELECT name, contact, conditions FROM funds WHERE resource_id=%s", (resource['id'],))
        else:
            c.execute("SELECT name, contact, conditions FROM funds WHERE resource_id=?", (resource['id'],))

        funds_dict[resource['id']] = [{'name': f[0], 'contact': f[1], 'conditions': f[2]} for f in c.fetchall()]

    conn.close()
    return jsonify({'resources': resources, 'funds': funds_dict})

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5001))
    db_type = "PostgreSQL" if USE_POSTGRES else "SQLite"
    print(f"🚀 Сервер запущено на порту {port}")
    print(f"📊 База даних: {db_type}")
    app.run(debug=False, host='0.0.0.0', port=port)
