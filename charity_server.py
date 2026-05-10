from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import sqlite3
import json
import os

app = Flask(__name__)
CORS(app)

DB_PATH = 'charity_funds.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS resources
                 (id TEXT PRIMARY KEY,
                  name TEXT NOT NULL,
                  description TEXT,
                  icon TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS funds
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  resource_id TEXT NOT NULL,
                  name TEXT NOT NULL,
                  contact TEXT,
                  conditions TEXT,
                  FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE)''')

    c.execute("SELECT COUNT(*) FROM resources")
    if c.fetchone()[0] == 0:
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
        c.executemany("INSERT INTO resources VALUES (?, ?, ?, ?)", default_resources)

        default_funds = [
            ('food', 'Червоний Хрест України', 'тел: 0-800-331-800, redcross.org.ua',
             'Для ВПО, малозабезпечених сімей. Потрібна довідка про статус ВПО або довідка про доходи.'),
            ('food', 'Карітас України', 'тел: (044) 235-65-05, caritas-ua.org',
             'Для сімей з дітьми, людей похилого віку. Реєстрація через місцеві відділення.'),
            ('medicine', 'Лікарі без кордонів', 'тел: (044) 585-52-66, msf.org.ua',
             'Безкоштовні медичні консультації та ліки. Для ВПО та малозабезпечених.'),
        ]
        c.executemany("INSERT INTO funds (resource_id, name, contact, conditions) VALUES (?, ?, ?, ?)",
                     default_funds)

    conn.commit()
    conn.close()

@app.route('/')
def index():
    return send_file('charity_funds.html')

@app.route('/api/resources', methods=['GET'])
def get_resources():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name, description, icon FROM resources")
    resources = [{'id': r[0], 'name': r[1], 'description': r[2], 'icon': r[3]}
                 for r in c.fetchall()]
    conn.close()
    return jsonify(resources)

@app.route('/api/resources', methods=['POST'])
def add_resource():
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
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
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE resources SET name=?, description=?, icon=? WHERE id=?",
             (data['name'], data['description'], data['icon'], resource_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/resources/<resource_id>', methods=['DELETE'])
def delete_resource(resource_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM funds WHERE resource_id=?", (resource_id,))
    c.execute("DELETE FROM resources WHERE id=?", (resource_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/funds/<resource_id>', methods=['GET'])
def get_funds(resource_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name, contact, conditions FROM funds WHERE resource_id=?", (resource_id,))
    funds = [{'id': f[0], 'name': f[1], 'contact': f[2], 'conditions': f[3]}
             for f in c.fetchall()]
    conn.close()
    return jsonify(funds)

@app.route('/api/funds', methods=['POST'])
def add_fund():
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO funds (resource_id, name, contact, conditions) VALUES (?, ?, ?, ?)",
             (data['resource_id'], data['name'], data['contact'], data['conditions']))
    conn.commit()
    fund_id = c.lastrowid
    conn.close()
    return jsonify({'success': True, 'id': fund_id})

@app.route('/api/funds/<int:fund_id>', methods=['PUT'])
def update_fund(fund_id):
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE funds SET name=?, contact=?, conditions=? WHERE id=?",
             (data['name'], data['contact'], data['conditions'], fund_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/funds/<int:fund_id>', methods=['DELETE'])
def delete_fund(fund_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM funds WHERE id=?", (fund_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/export', methods=['GET'])
def export_data():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT id, name, description, icon FROM resources")
    resources = [{'id': r[0], 'name': r[1], 'description': r[2], 'icon': r[3]}
                 for r in c.fetchall()]

    funds_dict = {}
    for resource in resources:
        c.execute("SELECT name, contact, conditions FROM funds WHERE resource_id=?",
                 (resource['id'],))
        funds_dict[resource['id']] = [{'name': f[0], 'contact': f[1], 'conditions': f[2]}
                                      for f in c.fetchall()]

    conn.close()
    return jsonify({'resources': resources, 'funds': funds_dict})

if __name__ == '__main__':
    init_db()
    print("🚀 Сервер запущено на http://localhost:5001")
    print("📊 База даних: charity_funds.db")
    app.run(debug=True, host='0.0.0.0', port=5001)
