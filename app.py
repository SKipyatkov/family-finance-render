from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from database import Database
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)
db = Database()

# Конфигурация
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')


@app.route('/')
def index():
    """Главная страница Mini App"""
    return render_template('index.html')


@app.route('/health')
def health():
    """Health check для Render"""
    return jsonify({
        'status': 'healthy',
        'service': 'Family Finance Bot',
        'timestamp': datetime.now().isoformat()
    })


# API для фронтенда
@app.route('/api/init', methods=['POST'])
def init_app():
    """Инициализация приложения"""
    data = request.json
    telegram_id = data.get('telegram_id')

    if not telegram_id:
        return jsonify({'error': 'telegram_id required'}), 400

    # Получаем или создаем пользователя
    user = db.get_user_by_telegram_id(telegram_id)
    if not user:
        db.add_user(telegram_id, f'user_{telegram_id}', 'Пользователь')
        user = db.get_user_by_telegram_id(telegram_id)

    return jsonify({
        'success': True,
        'user': user,
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/transactions', methods=['GET', 'POST'])
def transactions():
    """API для работы с транзакциями"""
    if request.method == 'GET':
        telegram_id = request.args.get('telegram_id', type=int)
        if not telegram_id:
            return jsonify({'error': 'telegram_id required'}), 400

        user = db.get_user_by_telegram_id(telegram_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        transactions_list = db.get_user_transactions(user['id'])
        return jsonify(transactions_list)

    elif request.method == 'POST':
        data = request.json
        telegram_id = data.get('telegram_id')

        if not telegram_id:
            return jsonify({'error': 'telegram_id required'}), 400

        user = db.get_user_by_telegram_id(telegram_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        transaction_id = db.add_transaction(
            user_id=user['id'],
            amount=data['amount'],
            category=data['category'],
            type=data['type'],
            description=data.get('description', ''),
            family_id=user.get('family_id')
        )

        return jsonify({
            'success': True,
            'transaction_id': transaction_id
        })


@app.route('/api/reports/monthly')
def monthly_report():
    """API для месячного отчета"""
    telegram_id = request.args.get('telegram_id', type=int)
    if not telegram_id:
        return jsonify({'error': 'telegram_id required'}), 400

    user = db.get_user_by_telegram_id(telegram_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    report = db.get_monthly_report(user['id'])
    return jsonify(report)


@app.route('/api/family/create', methods=['POST'])
def create_family():
    """Создание семьи"""
    data = request.json
    telegram_id = data.get('telegram_id')
    family_name = data.get('family_name')

    if not telegram_id or not family_name:
        return jsonify({'error': 'telegram_id and family_name required'}), 400

    user = db.get_user_by_telegram_id(telegram_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    family_id = db.create_family(user['id'], family_name)

    return jsonify({
        'success': True,
        'family_id': family_id,
        'message': f'Семья "{family_name}" создана'
    })


@app.route('/api/family/invite', methods=['POST'])
def create_invite():
    """Создание приглашения"""
    import uuid

    data = request.json
    telegram_id = data.get('telegram_id')

    if not telegram_id:
        return jsonify({'error': 'telegram_id required'}), 400

    user = db.get_user_by_telegram_id(telegram_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    invite_code = str(uuid.uuid4())[:8]
    db.create_invite(user['id'], invite_code)

    return jsonify({
        'success': True,
        'invite_code': invite_code,
        'message': 'Приглашение создано'
    })


# Статические файлы
@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)


# Webhook для Telegram бота
@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook для Telegram бота"""
    data = request.json
    print(f"Webhook received: {data}")

    # Здесь будет логика обработки сообщений от Telegram
    # Пока просто отвечаем OK

    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)