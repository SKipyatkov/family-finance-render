import os
import logging
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
from database import Database
from datetime import datetime
import asyncio

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class FamilyFinanceBot:
    def __init__(self, token):
        self.token = token
        self.db = Database()
        self.web_app_url = os.getenv('WEB_APP_URL', 'https://family-finance-bot-ccdb.onrender.com')

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start с красивым оформлением"""
        user = update.effective_user
        logger.info(f"User {user.id} started the bot")

        # Регистрируем пользователя
        telegram_id = user.id
        user_name = user.first_name or user.username or f"User_{telegram_id}"

        if not self.db.user_exists(telegram_id):
            self.db.add_user(telegram_id, user.username, user.first_name)
            welcome_msg = f"👋 *Привет, {user_name}!*\n\n"
            welcome_msg += "Добро пожаловать в *Семейную Копилку* — ваш личный помощник для управления бюджетом! 🏠💰"
        else:
            welcome_msg = f"✨ *С возвращением, {user_name}!*\n\n"
            welcome_msg += "Рады видеть вас снова в *Семейной Копилке*! 🎉"

        welcome_msg += "\n\n📊 *Что умеет бот:*"
        welcome_msg += "\n✅ Учет доходов и расходов"
        welcome_msg += "\n✅ Совместный бюджет с семьей"
        welcome_msg += "\n✅ Красивые графики и отчеты"
        welcome_msg += "\n✅ Планирование бюджета"
        welcome_msg += "\n✅ Синхронизация в реальном времени"

        # Создаем красивую клавиатуру
        keyboard = [
            [InlineKeyboardButton(
                "📱 ОТКРЫТЬ ПРИЛОЖЕНИЕ",
                web_app=WebAppInfo(url=f"{self.web_app_url}/?telegram_id={telegram_id}")
            )],
            [
                InlineKeyboardButton("💰 Доход", callback_data='quick_income'),
                InlineKeyboardButton("🛒 Расход", callback_data='quick_expense')
            ],
            [
                InlineKeyboardButton("📊 Отчет", callback_data='report'),
                InlineKeyboardButton("👨‍👩‍👧‍👦 Семья", callback_data='family')
            ],
            [
                InlineKeyboardButton("ℹ️ Помощь", callback_data='help'),
                InlineKeyboardButton("⚙️ Настройки", callback_data='settings')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Отправляем сообщение с разметкой
        await update.message.reply_text(
            welcome_msg,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )

        # Отправляем второе сообщение с инструкцией
        help_text = "🎯 *Быстрые команды:*\n"
        help_text += "`/add [сумма] [категория]` - добавить транзакцию\n"
        help_text += "`/report` - получить отчет\n"
        help_text += "`/balance` - проверить баланс\n"
        help_text += "`/family` - управление семьей\n"
        help_text += "`/help` - справка по командам\n\n"
        help_text += "💡 *Совет:* Используйте кнопки ниже для быстрого доступа к функциям!"

        await update.message.reply_text(
            help_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help"""
        help_text = """
🎯 *Семейная Копилка - Помощь*

📱 *Основные команды:*
`/start` - Начать работу с ботом
`/help` - Показать эту справку
`/add [сумма] [категория]` - Добавить транзакцию
`/report` - Получить отчет за месяц
`/balance` - Показать баланс
`/family` - Управление семьей
`/settings` - Настройки

💰 *Примеры использования:*
`/add 5000 Зарплата` - Добавить доход
`/add -1500 Еда` - Добавить расход
`/report` - Получить детальный отчет

👨‍👩‍👧‍👦 *Семейные функции:*
• Создайте семью через приложение
• Приглашайте членов семьи
• Совместный учет бюджета
• Общие отчеты

📊 *Отчеты и аналитика:*
• Ежемесячные отчеты
• Расходы по категориям
• Графики и диаграммы
• Планирование бюджета

💡 *Совет:* Используйте веб-приложение для полного доступа ко всем функциям!
        """

        keyboard = [[InlineKeyboardButton("📱 Открыть приложение",
                                          web_app=WebAppInfo(
                                              url=f"{self.web_app_url}/?telegram_id={update.effective_user.id}"))]]

        await update.message.reply_text(
            help_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard),
            disable_web_page_preview=True
        )

    async def add_transaction(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /add для быстрого добавления транзакций"""
        user = update.effective_user
        args = context.args

        if not args or len(args) < 2:
            await update.message.reply_text(
                "❌ *Использование:* `/add [сумма] [категория] [описание]`\n\n"
                "*Примеры:*\n"
                "`/add 5000 Зарплата` - доход\n"
                "`/add -1500 Еда обед в кафе` - расход",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        try:
            amount = float(args[0])
            category = args[1]
            description = ' '.join(args[2:]) if len(args) > 2 else ''

            transaction_type = 'income' if amount > 0 else 'expense'
            amount_abs = abs(amount)

            # Получаем пользователя
            db_user = self.db.get_user_by_telegram_id(user.id)
            if not db_user:
                self.db.add_user(user.id, user.username, user.first_name)
                db_user = self.db.get_user_by_telegram_id(user.id)

            # Добавляем транзакцию
            transaction_id = self.db.add_transaction(
                user_id=db_user['id'],
                amount=amount_abs,
                category=category,
                type=transaction_type,
                description=description
            )

            # Формируем эмодзи для типа
            type_emoji = "💰" if transaction_type == 'income' else "🛒"

            response = f"{type_emoji} *Транзакция добавлена!*\n\n"
            response += f"📝 *Тип:* {'Доход' if transaction_type == 'income' else 'Расход'}\n"
            response += f"💵 *Сумма:* {amount_abs} ₽\n"
            response += f"🏷️ *Категория:* {category}\n"
            if description:
                response += f"📋 *Описание:* {description}\n"
            response += f"🆔 *ID:* {transaction_id}\n"
            response += f"📅 *Время:* {datetime.now().strftime('%H:%M %d.%m.%Y')}"

            keyboard = [
                [InlineKeyboardButton("📱 Открыть приложение",
                                      web_app=WebAppInfo(url=f"{self.web_app_url}/?telegram_id={user.id}"))],
                [InlineKeyboardButton("📊 Отчет", callback_data='report')]
            ]

            await update.message.reply_text(
                response,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        except ValueError:
            await update.message.reply_text(
                "❌ Ошибка! Сумма должна быть числом.\n"
                "Пример: `/add 1500 Еда` или `/add -500 Транспорт`",
                parse_mode=ParseMode.MARKDOWN
            )

    async def balance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /balance"""
        user = update.effective_user

        db_user = self.db.get_user_by_telegram_id(user.id)
        if not db_user:
            await update.message.reply_text(
                "❌ Вы не зарегистрированы. Используйте /start для начала работы."
            )
            return

        report = self.db.get_monthly_report(db_user['id'])

        balance_text = f"💰 *ВАШ БАЛАНС*\n\n"
        balance_text += f"📅 *Период:* {datetime.now().strftime('%B %Y')}\n\n"
        balance_text += f"📈 *Доходы:* +{report['total_income']:,} ₽\n"
        balance_text += f"📉 *Расходы:* -{report['total_expense']:,} ₽\n"
        balance_text += f"━━━━━━━━━━━━━━━━━━\n"
        balance_text += f"💎 *Баланс:* {report['balance']:,} ₽\n\n"

        if report['categories']:
            balance_text += "📊 *Расходы по категориям:*\n"
            for cat in report['categories'][:5]:  # Показываем топ-5
                balance_text += f"• {cat['category']}: {cat['total']:,} ₽\n"

        keyboard = [
            [InlineKeyboardButton("📱 Подробный отчет",
                                  web_app=WebAppInfo(url=f"{self.web_app_url}/reports?telegram_id={user.id}"))],
            [InlineKeyboardButton("💰 Добавить доход", callback_data='quick_income'),
             InlineKeyboardButton("🛒 Добавить расход", callback_data='quick_expense')]
        ]

        await update.message.reply_text(
            balance_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def report_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /report"""
        user = update.effective_user

        db_user = self.db.get_user_by_telegram_id(user.id)
        if not db_user:
            await update.message.reply_text(
                "❌ Вы не зарегистрированы. Используйте /start для начала работы."
            )
            return

        report = self.db.get_monthly_report(db_user['id'])

        report_text = f"📊 *ОТЧЕТ ЗА МЕСЯЦ*\n\n"
        report_text += f"📅 *Период:* {datetime.now().strftime('%B %Y')}\n\n"

        # Статистика
        report_text += f"📈 *Общая статистика:*\n"
        report_text += f"└─ Доходы: +{report['total_income']:,} ₽\n"
        report_text += f"└─ Расходы: -{report['total_expense']:,} ₽\n"
        report_text += f"└─ Баланс: {report['balance']:,} ₽\n\n"

        if report['categories']:
            report_text += f"🏷️ *Топ расходов:*\n"
            for i, cat in enumerate(report['categories'][:5], 1):
                percentage = (cat['total'] / report['total_expense'] * 100) if report['total_expense'] > 0 else 0
                report_text += f"{i}. {cat['category']}: {cat['total']:,} ₽ ({percentage:.1f}%)\n"

        # Совет
        if report['balance'] < 0:
            report_text += "\n⚠️ *Внимание:* Отрицательный баланс!"
        elif report['balance'] > report['total_income'] * 0.3:
            report_text += "\n✅ *Отлично!* Хорошие накопления!"

        keyboard = [
            [InlineKeyboardButton("📱 Детальная аналитика",
                                  web_app=WebAppInfo(url=f"{self.web_app_url}/reports?telegram_id={user.id}"))],
            [InlineKeyboardButton("📈 Графики", callback_data='charts'),
             InlineKeyboardButton("📋 История", callback_data='history')]
        ]

        await update.message.reply_text(
            report_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def family_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /family"""
        user = update.effective_user

        db_user = self.db.get_user_by_telegram_id(user.id)
        if not db_user:
            await update.message.reply_text(
                "❌ Вы не зарегистрированы. Используйте /start для начала работы."
            )
            return

        if db_user.get('family_id'):
            # Пользователь в семье
            members = self.db.get_family_members(db_user['family_id'])

            family_text = f"👨‍👩‍👧‍👦 *ВАША СЕМЬЯ*\n\n"
            family_text += f"👥 *Участники ({len(members)}):*\n"

            for member in members:
                emoji = "👑" if member['id'] == db_user['id'] else "👤"
                name = member.get('first_name') or member.get('username') or f"Участник {member['id']}"
                family_text += f"{emoji} {name}\n"

            # Создаем инвайт-код
            invite_code = str(uuid.uuid4())[:8]
            self.db.create_invite(db_user['id'], invite_code)

            family_text += f"\n🔗 *Пригласительный код:*\n`{invite_code}`\n\n"
            family_text += "🎯 *Отправьте этот код другим участникам*"

        else:
            # Пользователь не в семье
            family_text = "👨‍👩‍👧‍👦 *УПРАВЛЕНИЕ СЕМЬЕЙ*\n\n"
            family_text += "Вы еще не создали семью. Семьи позволяют:\n"
            family_text += "✅ Вести совместный бюджет\n"
            family_text += "✅ Видеть общие отчеты\n"
            family_text += "✅ Контролировать общие расходы\n\n"
            family_text += "Создайте семью или присоединитесь к существующей!"

        keyboard = [
            [InlineKeyboardButton("📱 Управление семьей",
                                  web_app=WebAppInfo(url=f"{self.web_app_url}/family?telegram_id={user.id}"))]
        ]

        if not db_user.get('family_id'):
            keyboard.append([
                InlineKeyboardButton("🏠 Создать семью", callback_data='create_family'),
                InlineKeyboardButton("🔗 Присоединиться", callback_data='join_family')
            ])

        await update.message.reply_text(
            family_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка callback-запросов"""
        query = update.callback_query
        await query.answer()

        data = query.data
        user = query.from_user
        telegram_id = user.id

        if data == 'quick_income':
            # Быстрое добавление дохода
            keyboard = [
                [InlineKeyboardButton("💼 Зарплата", callback_data='income_salary_10000'),
                 InlineKeyboardButton("🎁 Подарок", callback_data='income_gift_5000')],
                [InlineKeyboardButton("📈 Инвестиции", callback_data='income_investment_3000'),
                 InlineKeyboardButton("🛠️ Фриланс", callback_data='income_freelance_7000')],
                [InlineKeyboardButton("📱 Ввести сумму", callback_data='custom_income')]
            ]
            await query.edit_message_text(
                "💰 *ДОБАВЛЕНИЕ ДОХОДА*\n\nВыберите категорию или укажите свою сумму:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        elif data == 'quick_expense':
            # Быстрое добавление расхода
            keyboard = [
                [InlineKeyboardButton("🍔 Еда", callback_data='expense_food_1500'),
                 InlineKeyboardButton("🚌 Транспорт", callback_data='expense_transport_800')],
                [InlineKeyboardButton("🏠 Коммуналка", callback_data='expense_utilities_5000'),
                 InlineKeyboardButton("🎬 Развлечения", callback_data='expense_entertainment_2000')],
                [InlineKeyboardButton("🛍️ Покупки", callback_data='expense_shopping_3000'),
                 InlineKeyboardButton("🏥 Здоровье", callback_data='expense_health_1500')],
                [InlineKeyboardButton("📱 Ввести сумму", callback_data='custom_expense')]
            ]
            await query.edit_message_text(
                "🛒 *ДОБАВЛЕНИЕ РАСХОДА*\n\nВыберите категорию или укажите свою сумму:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        elif data.startswith('income_') or data.startswith('expense_'):
            # Обработка быстрой транзакции
            parts = data.split('_')
            if len(parts) >= 3:
                trans_type = parts[0]  # income или expense
                category = parts[1]
                amount = float(parts[2]) if len(parts) > 2 else 0

                db_user = self.db.get_user_by_telegram_id(telegram_id)
                if db_user:
                    transaction_id = self.db.add_transaction(
                        user_id=db_user['id'],
                        amount=amount,
                        category=category,
                        type=trans_type,
                        description=f"Быстрая операция через бота"
                    )

                    emoji = "💰" if trans_type == 'income' else "🛒"
                    await query.edit_message_text(
                        f"{emoji} *Операция добавлена!*\n\n"
                        f"💵 Сумма: {amount:,} ₽\n"
                        f"🏷️ Категория: {category}\n"
                        f"✅ Тип: {'Доход' if trans_type == 'income' else 'Расход'}\n\n"
                        f"Используйте /report для просмотра отчетов.",
                        parse_mode=ParseMode.MARKDOWN
                    )

        elif data == 'report':
            await self.report_command_for_callback(query, telegram_id)

        elif data == 'family':
            await self.family_command_for_callback(query, telegram_id)

        elif data == 'help':
            await self.help_command_for_callback(query)

        elif data == 'create_family':
            keyboard = [[InlineKeyboardButton("📱 Создать в приложении",
                                              web_app=WebAppInfo(
                                                  url=f"{self.web_app_url}/family/create?telegram_id={telegram_id}"))]]
            await query.edit_message_text(
                "🏠 *СОЗДАНИЕ СЕМЬИ*\n\n"
                "Для создания семьи откройте веб-приложение.\n"
                "Там вы сможете:\n"
                "✅ Указать название семьи\n"
                "✅ Настроить общие категории\n"
                "✅ Пригласить участников\n\n"
                "Нажмите кнопку ниже:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    async def report_command_for_callback(self, query, telegram_id):
        """Вспомогательный метод для callback"""
        db_user = self.db.get_user_by_telegram_id(telegram_id)
        if db_user:
            report = self.db.get_monthly_report(db_user['id'])

            report_text = f"📊 *ОТЧЕТ*\n\n"
            report_text += f"💰 Баланс: {report['balance']:,} ₽\n"
            report_text += f"📈 Доходы: {report['total_income']:,} ₽\n"
            report_text += f"📉 Расходы: {report['total_expense']:,} ₽\n\n"

            if report['categories']:
                report_text += "🏷️ Топ категорий:\n"
                for cat in report['categories'][:3]:
                    report_text += f"• {cat['category']}: {cat['total']:,} ₽\n"

            keyboard = [
                [InlineKeyboardButton("📱 Подробный отчет",
                                      web_app=WebAppInfo(url=f"{self.web_app_url}/reports?telegram_id={telegram_id}"))],
                [InlineKeyboardButton("📈 Графики", callback_data='charts')]
            ]

            await query.edit_message_text(
                report_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    async def family_command_for_callback(self, query, telegram_id):
        """Вспомогательный метод для callback"""
        db_user = self.db.get_user_by_telegram_id(telegram_id)
        if db_user and db_user.get('family_id'):
            members = self.db.get_family_members(db_user['family_id'])

            family_text = f"👨‍👩‍👧‍👦 *СЕМЬЯ*\n\n"
            family_text += f"👥 Участники: {len(members)}\n\n"

            for member in members[:3]:
                name = member.get('first_name') or member.get('username') or f"Участник"
                family_text += f"👤 {name}\n"

            if len(members) > 3:
                family_text += f"... и ещё {len(members) - 3}\n"

            keyboard = [[InlineKeyboardButton("📱 Управление",
                                              web_app=WebAppInfo(
                                                  url=f"{self.web_app_url}/family?telegram_id={telegram_id}"))]]

            await query.edit_message_text(
                family_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    async def help_command_for_callback(self, query):
        """Вспомогательный метод для callback"""
        help_text = "🎯 *Быстрые команды:*\n\n"
        help_text += "`/add [сумма] [категория]`\n"
        help_text += "`/report` - отчет\n"
        help_text += "`/balance` - баланс\n"
        help_text += "`/family` - семья\n\n"
        help_text += "💡 Используйте кнопки или команды!"

        keyboard = [
            [InlineKeyboardButton("📱 Открыть приложение",
                                  web_app=WebAppInfo(url=f"{self.web_app_url}/?telegram_id={query.from_user.id}"))],
            [
                InlineKeyboardButton("💰 Доход", callback_data='quick_income'),
                InlineKeyboardButton("🛒 Расход", callback_data='quick_expense')
            ]
        ]

        await query.edit_message_text(
            help_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        message = update.message
        text = message.text

        # Игнорируем команды (они обрабатываются отдельно)
        if text.startswith('/'):
            return

        # Приветствие на обычные сообщения
        greetings = ['привет', 'hello', 'hi', 'здравствуй', 'добрый день']
        if text.lower() in greetings:
            await message.reply_text(
                f"👋 Привет, {update.effective_user.first_name}!\n"
                f"Используйте /start для начала работы или /help для справки."
            )
            return

        # Ответ на другие сообщения
        await message.reply_text(
            "🤖 Я финансовый бот-помощник!\n\n"
            "Используйте команды:\n"
            "• /start - Начать работу\n"
            "• /help - Получить справку\n"
            "• /add - Добавить транзакцию\n"
            "• /report - Получить отчет\n\n"
            "Или воспользуйтесь кнопками в меню!"
        )

    def run(self):
        """Запуск бота"""
        application = Application.builder().token(self.token).build()

        # Регистрация обработчиков команд
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("add", self.add_transaction))
        application.add_handler(CommandHandler("balance", self.balance_command))
        application.add_handler(CommandHandler("report", self.report_command))
        application.add_handler(CommandHandler("family", self.family_command))

        # Обработчики callback и сообщений
        application.add_handler(CallbackQueryHandler(self.handle_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        # Запуск webhook для Render
        print(f"🤖 Бот запускается...")
        print(f"🌐 Webhook URL: {self.web_app_url}/webhook")

        application.run_webhook(
            listen="0.0.0.0",
            port=int(os.getenv('PORT', 5000)),
            url_path=self.token,
            webhook_url=f"{self.web_app_url}/webhook",
            secret_token='WEBHOOK_SECRET'
        )


if __name__ == '__main__':
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("❌ ОШИБКА: TELEGRAM_BOT_TOKEN не установлен!")
        exit(1)

    bot = FamilyFinanceBot(token)
    bot.run()