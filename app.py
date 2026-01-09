from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from database import Database
import json
import os
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)  # Разрешаем CORS для всех доменов
db = Database()

# Конфигурация
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')


@app.route('/')
def index():
    """Главная страница Mini App"""
    user_id = request.args.get('user_id', type=int)
    return render_template('index.html', user_id=user_id)


@app.route('/dashboard')
def dashboard():
    """Панель управления"""
    user_id = request.args.get('user_id', type=int)
    if not user_id:
        return jsonify({'error': 'User ID required'}), 400

    # Получаем данные для дашборда
    user_data = db.get_user(user_id)
    family_data = db.get_family_data(user_id)
    recent_transactions = db.get_recent_transactions(user_id, limit=5)
    monthly_report = db.get_monthly_report(user_id)

    return render_template('dashboard.html',
                           user=user_data,
                           family=family_data,
                           transactions=recent_transactions,
                           report=monthly_report)


# API endpoints
@app.route('/api/transactions', methods=['GET', 'POST'])
def transactions():
    """API для работы с транзакциями"""
    if request.method == 'GET':
        user_id = request.args.get('user_id', type=int)
        if not user_id:
            return jsonify({'error': 'User ID required'}), 400

        transactions = db.get_user_transactions(user_id)
        return jsonify(transactions)

    elif request.method == 'POST':
        data = request.json
        transaction_id = db.add_transaction(
            user_id=data['user_id'],
            amount=data['amount'],
            category=data['category'],
            type=data['type'],
            description=data.get('description', ''),
            family_id=data.get('family_id')
        )
        return jsonify({'success': True, 'transaction_id': transaction_id})


@app.route('/api/family', methods=['GET', 'POST'])
def family():
    """API для работы с семьей"""
    user_id = request.args.get('user_id', type=int)

    if request.method == 'GET':
        family_data = db.get_family_data(user_id)
        return jsonify(family_data)

    elif request.method == 'POST':
        data = request.json
        action = data.get('action')

        if action == 'create':
            family_id = db.create_family(user_id, data['family_name'])
            return jsonify({'success': True, 'family_id': family_id})

        elif action == 'join':
            invite_code = data['invite_code']
            success = db.join_family_by_invite(user_id, invite_code)
            return jsonify({'success': success})


@app.route('/api/reports/monthly')
def monthly_report():
    """API для месячного отчета"""
    user_id = request.args.get('user_id', type=int)
    report = db.get_monthly_report(user_id)
    return jsonify(report)


@app.route('/api/reports/categories')
def category_report():
    """API для отчета по категориям"""
    user_id = request.args.get('user_id', type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    report = db.get_category_report(user_id, start_date, end_date)
    return jsonify(report)


@app.route('/api/sync', methods=['POST'])
def sync():
    """API для синхронизации в реальном времени"""
    data = request.json
    user_id = data['user_id']

    # Получаем последние изменения
    last_sync = data.get('last_sync')
    updates = db.get_updates_since(user_id, last_sync)

    return jsonify({
        'success': True,
        'updates': updates,
        'server_time': datetime.now().isoformat()
    })


# Статические файлы
@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)


# Health check для Render
@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'Family Finance Mini App'
    })


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.getenv('FLASK_ENV') == 'development')