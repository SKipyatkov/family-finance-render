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
                           NULL, -- 'income' или 'expense'
                           description
                           TEXT,
                           date
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           FOREIGN
                           KEY
                       (
                           user_id
                       ) REFERENCES users
                       (
                           id
                       )
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
                           FALSE,
                           created_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP
                       )
                       ''')

        # Таблица бюджетов
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS budgets
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
                           category
                           TEXT
                           NOT
                           NULL,
                           amount_limit
                           REAL
                           NOT
                           NULL,
                           period
                           TEXT
                           DEFAULT
                           'monthly', -- 'daily', 'weekly', 'monthly'
                           created_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP
                       )
                       ''')

        conn.commit()
        conn.close()

    def add_user(self, telegram_id: int, username: str, first_name: str = None):
        """Добавление нового пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                           INSERT
                           OR IGNORE INTO users (telegram_id, username, first_name)
                VALUES (?, ?, ?)
                           ''', (telegram_id, username, first_name))
            conn.commit()
        finally:
            conn.close()

    def user_exists(self, telegram_id: int) -> bool:
        """Проверка существования пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT 1 FROM users WHERE telegram_id = ?', (telegram_id,))
        exists = cursor.fetchone() is not None

        conn.close()
        return exists

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
                          OR t.family_id IN (SELECT family_id
                                             FROM users
                                             WHERE id = ?)
                       ORDER BY t.date DESC LIMIT ?
                       ''', (user_id, user_id, limit))

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
            'categories': categories,
            'month': datetime.now().strftime('%B %Y')
        }

    def create_family(self, user_id: int, family_name: str) -> int:
        """Создание новой семьи"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('INSERT INTO families (name, created_by) VALUES (?, ?)',
                       (family_name, user_id))
        family_id = cursor.lastrowid

        # Обновляем family_id у создателя
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
                       ''', (code, user_id, expires_at.isoformat()))

        conn.commit()
        conn.close()

    def join_family_by_invite(self, user_id: int, invite_code: str) -> bool:
        """Присоединение к семье по инвайт-коду"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Проверяем инвайт
        cursor.execute('''
                       SELECT created_by, expires_at
                       FROM invites
                       WHERE code = ?
                         AND used = FALSE
                       ''', (invite_code,))

        invite = cursor.fetchone()
        if not invite:
            conn.close()
            return False

        # Проверяем срок действия
        expires_at = datetime.fromisoformat(invite['expires_at'])
        if datetime.now() > expires_at:
            conn.close()
            return False

        # Получаем family_id создателя
        cursor.execute('SELECT family_id FROM users WHERE id = ?', (invite['created_by'],))
        creator = cursor.fetchone()

        if creator and creator['family_id']:
            # Обновляем family_id пользователя
            cursor.execute('UPDATE users SET family_id = ? WHERE id = ?',
                           (creator['family_id'], user_id))

            # Помечаем инвайт как использованный
            cursor.execute('UPDATE invites SET used = TRUE WHERE code = ?', (invite_code,))

            conn.commit()
            conn.close()
            return True

        conn.close()
        return False

    # ===== НОВЫЕ МЕТОДЫ (которых не хватало) =====

    def get_category_report(self, user_id: int, start_date=None, end_date=None) -> Dict:
        """Получение отчета по категориям"""
        conn = self.get_connection()
        cursor = conn.cursor()

        query = '''
                SELECT category, \
                       type, \
                       SUM(amount) as total, \
                       COUNT(*) as count
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

        query += " GROUP BY category, type ORDER BY total DESC"

        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]

        # Формируем структурированный отчет
        report = {
            'by_category': {},
            'total_income': 0,
            'total_expense': 0,
            'period': {
                'start': start_date,
                'end': end_date or datetime.now().isoformat()
            }
        }

        for item in results:
            category = item['category']
            if category not in report['by_category']:
                report['by_category'][category] = {
                    'income': 0,
                    'expense': 0,
                    'total': 0
                }

            if item['type'] == 'income':
                report['by_category'][category]['income'] = item['total']
                report['total_income'] += item['total']
            else:
                report['by_category'][category]['expense'] = item['total']
                report['total_expense'] += item['total']

            report['by_category'][category]['total'] = (
                    report['by_category'][category]['income'] -
                    report['by_category'][category]['expense']
            )

        conn.close()
        return report

    def get_updates_since(self, user_id: int, last_sync: str = None) -> Dict:
        """Получение обновлений после указанного времени"""
        conn = self.get_connection()
        cursor = conn.cursor()

        if not last_sync:
            last_sync = '1970-01-01 00:00:00'

        # Получаем новые транзакции
        cursor.execute('''
                       SELECT t.*,
                              u.username as user_name
                       FROM transactions t
                                LEFT JOIN users u ON t.user_id = u.id
                       WHERE (t.user_id = ? OR t.family_id IN (SELECT family_id
                                                               FROM users
                                                               WHERE id = ?))
                         AND t.date > ?
                       ORDER BY t.date DESC
                       ''', (user_id, user_id, last_sync))

        transactions = [dict(row) for row in cursor.fetchall()]

        # Получаем обновления семьи
        cursor.execute('''
                       SELECT *
                       FROM families
                       WHERE id IN (SELECT family_id
                                    FROM users
                                    WHERE id = ?)
                         AND created_at > ?
                       ''', (user_id, last_sync))

        family_updates = [dict(row) for row in cursor.fetchall()]

        # Получаем новые приглашения
        cursor.execute('''
                       SELECT *
                       FROM invites
                       WHERE created_by = ?
                         AND created_at > ?
                       ''', (user_id, last_sync))

        invites = [dict(row) for row in cursor.fetchall()]

        conn.close()

        return {
            'transactions': transactions,
            'family_updates': family_updates,
            'invites': invites,
            'last_sync': datetime.now().isoformat(),
            'count': len(transactions) + len(family_updates) + len(invites)
        }

    def get_user(self, user_id: int) -> Dict:
        """Получение данных пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
                       SELECT u.*,
                              f.name               as family_name,
                              COUNT(DISTINCT t.id) as transaction_count
                       FROM users u
                                LEFT JOIN families f ON u.family_id = f.id
                                LEFT JOIN transactions t ON u.id = t.user_id
                       WHERE u.id = ?
                       GROUP BY u.id
                       ''', (user_id,))

        user = cursor.fetchone()
        conn.close()

        if user:
            return dict(user)

        # Если пользователь не найден, создаем заглушку
        return {
            'id': user_id,
            'telegram_id': 0,
            'username': 'Неизвестный',
            'first_name': 'Пользователь',
            'family_id': None,
            'family_name': None,
            'transaction_count': 0
        }

    def get_family_data(self, user_id: int) -> Dict:
        """Получение данных семьи пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Получаем данные семьи
        cursor.execute('''
                       SELECT f.*,
                              u.username           as creator_name,
                              COUNT(DISTINCT m.id) as member_count,
                              COUNT(DISTINCT t.id) as family_transactions
                       FROM families f
                                JOIN users u ON f.created_by = u.id
                                LEFT JOIN users m ON f.id = m.family_id
                                LEFT JOIN transactions t ON f.id = t.family_id
                       WHERE f.id IN (SELECT family_id
                                      FROM users
                                      WHERE id = ?)
                       GROUP BY f.id
                       ''', (user_id,))

        family = cursor.fetchone()

        if not family:
            conn.close()
            return {
                'has_family': False,
                'message': 'Вы еще не присоединились к семье'
            }

        # Получаем членов семьи
        cursor.execute('''
                       SELECT id,
                              username,
                              first_name,
                              created_at
                       FROM users
                       WHERE family_id = ?
                       ORDER BY created_at DESC
                       ''', (family['id'],))

        members = [dict(row) for row in cursor.fetchall()]

        # Получаем семейные транзакции
        cursor.execute('''
                       SELECT t.*,
                              u.username as user_name
                       FROM transactions t
                                JOIN users u ON t.user_id = u.id
                       WHERE t.family_id = ?
                       ORDER BY t.date DESC LIMIT 10
                       ''', (family['id'],))

        family_transactions = [dict(row) for row in cursor.fetchall()]

        conn.close()

        return {
            'has_family': True,
            'family': dict(family),
            'members': members,
            'recent_transactions': family_transactions,
            'member_count': len(members)
        }

    def get_recent_transactions(self, user_id: int, limit: int = 5) -> List[Dict]:
        """Получение последних транзакций"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
                       SELECT t.*,
                              u.username as user_name
                       FROM transactions t
                                LEFT JOIN users u ON t.user_id = u.id
                       WHERE t.user_id = ?
                          OR t.family_id IN (SELECT family_id
                                             FROM users
                                             WHERE id = ?)
                       ORDER BY t.date DESC LIMIT ?
                       ''', (user_id, user_id, limit))

        transactions = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return transactions

    def get_transaction_by_id(self, transaction_id: int) -> Dict:
        """Получение транзакции по ID"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
                       SELECT t.*,
                              u.username as user_name
                       FROM transactions t
                                LEFT JOIN users u ON t.user_id = u.id
                       WHERE t.id = ?
                       ''', (transaction_id,))

        transaction = cursor.fetchone()
        conn.close()

        return dict(transaction) if transaction else None

    def delete_transaction(self, transaction_id: int) -> bool:
        """Удаление транзакции"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM transactions WHERE id = ?', (transaction_id,))
        deleted = cursor.rowcount > 0

        conn.commit()
        conn.close()
        return deleted

    def get_user_by_telegram_id(self, telegram_id: int) -> Dict:
        """Получение пользователя по Telegram ID"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
        user = cursor.fetchone()
        conn.close()

        return dict(user) if user else None

    def update_user_family(self, user_id: int, family_id: int) -> bool:
        """Обновление family_id пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('UPDATE users SET family_id = ? WHERE id = ?',
                       (family_id, user_id))

        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return updated

    def get_family_members(self, family_id: int) -> List[Dict]:
        """Получение членов семьи"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
                       SELECT id,
                              telegram_id,
                              username,
                              first_name,
                              created_at
                       FROM users
                       WHERE family_id = ?
                       ORDER BY created_at
                       ''', (family_id,))

        members = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return members

    def get_family_transactions(self, family_id: int, limit: int = 50) -> List[Dict]:
        """Получение транзакций семьи"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
                       SELECT t.*,
                              u.username as user_name
                       FROM transactions t
                                JOIN users u ON t.user_id = u.id
                       WHERE t.family_id = ?
                       ORDER BY t.date DESC LIMIT ?
                       ''', (family_id, limit))

        transactions = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return transactions

    def get_budget_report(self, user_id: int) -> Dict:
        """Получение отчета по бюджетам"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Получаем установленные бюджеты
        cursor.execute('''
                       SELECT *
                       FROM budgets
                       WHERE user_id = ?
                          OR family_id IN (SELECT family_id
                                           FROM users
                                           WHERE id = ?)
                       ''', (user_id, user_id))

        budgets = [dict(row) for row in cursor.fetchall()]

        # Для каждого бюджета считаем фактические расходы
        for budget in budgets:
            cursor.execute('''
                           SELECT COALESCE(SUM(amount), 0) as spent
                           FROM transactions
                           WHERE category = ?
                             AND type = 'expense'
                             AND user_id = ?
                             AND date >= datetime('now'
                               , 'start of month')
                           ''', (budget['category'], user_id))

            spent = cursor.fetchone()[0]
            budget['spent'] = spent
            budget['remaining'] = budget['amount_limit'] - spent
            budget['percentage'] = (spent / budget['amount_limit'] * 100) if budget['amount_limit'] > 0 else 0

        conn.close()

        return {
            'budgets': budgets,
            'total_budgets': len(budgets),
            'total_limit': sum(b['amount_limit'] for b in budgets),
            'total_spent': sum(b['spent'] for b in budgets)
        }

    def set_budget(self, user_id: int, category: str, amount_limit: float,
                   period: str = 'monthly', family_id: int = None) -> int:
        """Установка бюджета"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Удаляем старый бюджет для этой категории
        cursor.execute('''
                       DELETE
                       FROM budgets
                       WHERE user_id = ?
                         AND category = ?
                         AND period = ?
                       ''', (user_id, category, period))

        # Добавляем новый бюджет
        cursor.execute('''
                       INSERT INTO budgets (user_id, family_id, category, amount_limit, period)
                       VALUES (?, ?, ?, ?, ?)
                       ''', (user_id, family_id, category, amount_limit, period))

        budget_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return budget_id