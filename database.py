import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os


class Database:
    def __init__(self, db_path: str = "family_finance.db"):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        """Создание подключения к БД"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Инициализация базы данных"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Таблица пользователей
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS users
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           telegram_id
                           INTEGER
                           UNIQUE
                           NOT
                           NULL,
                           username
                           TEXT,
                           first_name
                           TEXT,
                           created_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           family_id
                           INTEGER
                       )
                       ''')

        # Таблица семей
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS families
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           name
                           TEXT
                           NOT
                           NULL,
                           created_by
                           INTEGER
                           NOT
                           NULL,
                           created_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP
                       )
                       ''')

        # Таблица транзакций
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS transactions
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           user_id
                           INTEGER
                           NOT
                           NULL,
                           family_id
                           INTEGER,
                           amount
                           REAL
                           NOT
                           NULL,
                           currency
                           TEXT
                           DEFAULT
                           'RUB',
                           category
                           TEXT
                           NOT
                           NULL,
                           type
                           TEXT
                           NOT
                           NULL,
                           description
                           TEXT,
                           date
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP
                       )
                       ''')

        # Таблица приглашений
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS invites
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           code
                           TEXT
                           UNIQUE
                           NOT
                           NULL,
                           created_by
                           INTEGER
                           NOT
                           NULL,
                           expires_at
                           TIMESTAMP
                           NOT
                           NULL,
                           used
                           BOOLEAN
                           DEFAULT
                           FALSE
                       )
                       ''')

        conn.commit()
        conn.close()

    def add_user(self, telegram_id: int, username: str, first_name: str = None):
        """Добавление нового пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
                       INSERT
                       OR IGNORE INTO users (telegram_id, username, first_name)
            VALUES (?, ?, ?)
                       ''', (telegram_id, username, first_name))

        conn.commit()
        conn.close()

    def user_exists(self, telegram_id: int) -> bool:
        """Проверка существования пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT 1 FROM users WHERE telegram_id = ?', (telegram_id,))
        exists = cursor.fetchone() is not None

        conn.close()
        return exists

    def get_user_by_telegram_id(self, telegram_id: int) -> Dict:
        """Получение пользователя по Telegram ID"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
        user = cursor.fetchone()
        conn.close()

        return dict(user) if user else None

    def add_transaction(self, user_id: int, amount: float, category: str,
                        type: str, description: str = '', family_id: int = None) -> int:
        """Добавление транзакции"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
                       INSERT INTO transactions (user_id, family_id, amount, category, type, description)
                       VALUES (?, ?, ?, ?, ?, ?)
                       ''', (user_id, family_id, amount, category, type, description))

        transaction_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return transaction_id

    def get_user_transactions(self, user_id: int, limit: int = 50) -> List[Dict]:
        """Получение транзакций пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
                       SELECT t.*, u.username
                       FROM transactions t
                                LEFT JOIN users u ON t.user_id = u.id
                       WHERE t.user_id = ?
                       ORDER BY t.date DESC LIMIT ?
                       ''', (user_id, limit))

        transactions = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return transactions

    def get_monthly_report(self, user_id: int) -> Dict:
        """Получение месячного отчета"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Доходы за текущий месяц
        cursor.execute('''
                       SELECT COALESCE(SUM(amount), 0) as total_income
                       FROM transactions
                       WHERE user_id = ?
                         AND type = 'income'
                         AND strftime('%Y-%m', date) = strftime('%Y-%m', 'now')
                       ''', (user_id,))
        total_income = cursor.fetchone()[0]

        # Расходы за текущий месяц
        cursor.execute('''
                       SELECT COALESCE(SUM(amount), 0) as total_expense
                       FROM transactions
                       WHERE user_id = ?
                         AND type = 'expense'
                         AND strftime('%Y-%m', date) = strftime('%Y-%m', 'now')
                       ''', (user_id,))
        total_expense = cursor.fetchone()[0]

        # Расходы по категориям
        cursor.execute('''
                       SELECT category, SUM(amount) as total
                       FROM transactions
                       WHERE user_id = ?
                         AND type = 'expense'
                         AND strftime('%Y-%m', date) = strftime('%Y-%m', 'now')
                       GROUP BY category
                       ORDER BY total DESC
                       ''', (user_id,))
        categories = [dict(row) for row in cursor.fetchall()]

        conn.close()

        return {
            'total_income': total_income,
            'total_expense': total_expense,
            'balance': total_income - total_expense,
            'categories': categories
        }

    def get_category_report(self, user_id: int, start_date=None, end_date=None) -> Dict:
        """Получение отчета по категориям"""
        conn = self.get_connection()
        cursor = conn.cursor()

        query = '''
                SELECT category, type, SUM(amount) as total
                FROM transactions
                WHERE user_id = ? \
                '''
        params = [user_id]

        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)

        query += " GROUP BY category, type"

        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]

        report = {'categories': {}}
        for item in results:
            category = item['category']
            if category not in report['categories']:
                report['categories'][category] = {'income': 0, 'expense': 0}

            if item['type'] == 'income':
                report['categories'][category]['income'] = item['total']
            else:
                report['categories'][category]['expense'] = item['total']

        conn.close()
        return report

    def get_updates_since(self, user_id: int, last_sync: str = None) -> Dict:
        """Получение обновлений после указанного времени"""
        conn = self.get_connection()
        cursor = conn.cursor()

        if not last_sync:
            last_sync = '1970-01-01'

        cursor.execute('''
                       SELECT *
                       FROM transactions
                       WHERE user_id = ? AND date > ?
                       ORDER BY date DESC
                       ''', (user_id, last_sync))

        transactions = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return {
            'transactions': transactions,
            'count': len(transactions)
        }

    def create_family(self, user_id: int, family_name: str) -> int:
        """Создание новой семьи"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('INSERT INTO families (name, created_by) VALUES (?, ?)',
                       (family_name, user_id))
        family_id = cursor.lastrowid

        cursor.execute('UPDATE users SET family_id = ? WHERE id = ?',
                       (family_id, user_id))

        conn.commit()
        conn.close()
        return family_id

    def create_invite(self, user_id: int, code: str, expires_hours: int = 24):
        """Создание приглашения"""
        conn = self.get_connection()
        cursor = conn.cursor()

        expires_at = datetime.now() + timedelta(hours=expires_hours)

        cursor.execute('''
                       INSERT INTO invites (code, created_by, expires_at)
                       VALUES (?, ?, ?)
                       ''', (code, user_id, expires_at))

        conn.commit()
        conn.close()

    def join_family(self, user_id: int, family_id: int) -> bool:
        """Присоединение к семье"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('UPDATE users SET family_id = ? WHERE id = ?',
                       (family_id, user_id))

        success = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return success

    def get_family_members(self, family_id: int) -> List[Dict]:
        """Получение членов семьи"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
                       SELECT id, username, first_name
                       FROM users
                       WHERE family_id = ?
                       ''', (family_id,))

        members = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return members