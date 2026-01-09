import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from database import Database
import json

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
        self.web_app_url = os.getenv('WEB_APP_URL', 'https://your-webapp-url.onrender.com')

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        logger.info(f"User {user.id} started the bot")

        # Регистрируем пользователя в базе
        user_id = user.id
        user_name = user.first_name or user.username

        if not self.db.user_exists(user_id):
            self.db.add_user(user_id, user_name)
            welcome_msg = f"👋 Привет, {user_name}!\n\nДобро пожаловать в семейный финансовый бот 'Копилка'!"
        else:
            welcome_msg = f"С возвращением, {user_name}! 🏠"

        # Создаем клавиатуру с кнопкой Mini App
        keyboard = [
            [InlineKeyboardButton("📱 Открыть Mini App",
                                  web_app=WebAppInfo(url=f"{self.web_app_url}/?user_id={user_id}"))],
            [InlineKeyboardButton("💰 Добавить доход", callback_data='add_income'),
             InlineKeyboardButton("🛒 Добавить расход", callback_data='add_expense')],
            [InlineKeyboardButton("📊 Отчеты", callback_data='reports'),
             InlineKeyboardButton("👨‍👩‍👧‍👦 Семья", callback_data='family')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            welcome_msg + "\n\nВыберите действие:",
            reply_markup=reply_markup
        )

    async def add_family_member(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Генерация ссылки-приглашения в семью"""
        user_id = update.effective_user.id

        # Создаем уникальный код приглашения
        import uuid
        invite_code = str(uuid.uuid4())[:8]
        self.db.create_invite(user_id, invite_code)

        invite_link = f"https://t.me/{(await context.bot.get_me()).username}?start=invite_{invite_code}"

        await update.message.reply_text(
            f"🔗 Пригласите члена семьи:\n\n{invite_link}\n\n"
            f"Код действителен 24 часа."
        )

    async def quick_add_transaction(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Быстрое добавление транзакции через inline-кнопки"""
        query = update.callback_query
        await query.answer()

        transaction_type = query.data.split('_')[1]  # 'income' или 'expense'

        keyboard = [
            [InlineKeyboardButton("🍔 Еда", callback_data=f'quick_{transaction_type}_food_500')],
            [InlineKeyboardButton("🚌 Транспорт", callback_data=f'quick_{transaction_type}_transport_300')],
            [InlineKeyboardButton("🏠 Коммуналка", callback_data=f'quick_{transaction_type}_utilities_2000')],
            [InlineKeyboardButton("🎬 Развлечения", callback_data=f'quick_{transaction_type}_entertainment_1000')],
        ]

        await query.edit_message_text(
            text=f"Выберите категорию для {'дохода' if transaction_type == 'income' else 'расхода'}:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка callback-запросов"""
        query = update.callback_query
        data = query.data

        if data.startswith('quick_'):
            # Обработка быстрой транзакции
            _, trans_type, category, amount = data.split('_')
            user_id = query.from_user.id

            # Сохраняем транзакцию
            self.db.add_transaction(
                user_id=user_id,
                amount=float(amount),
                category=category,
                type=trans_type,
                description=f"Быстрый {trans_type}"
            )

            await query.answer(f"{'Доход' if trans_type == 'income' else 'Расход'} добавлен!")
            await query.edit_message_text(text="✅ Транзакция сохранена!")

        elif data == 'reports':
            # Показываем отчеты
            user_id = query.from_user.id
            report = self.db.get_monthly_report(user_id)

            await query.edit_message_text(
                text=f"📊 Отчет за месяц:\n\n"
                     f"💰 Доходы: {report['total_income']} ₽\n"
                     f"🛒 Расходы: {report['total_expense']} ₽\n"
                     f"📈 Баланс: {report['balance']} ₽",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📱 Детальный отчет",
                                         web_app=WebAppInfo(url=f"{self.web_app_url}/reports?user_id={user_id}"))
                ]])
            )

    def run(self):
        """Запуск бота"""
        application = Application.builder().token(self.token).build()

        # Регистрация обработчиков
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("invite", self.add_family_member))
        application.add_handler(CallbackQueryHandler(self.handle_callback))

        # Запуск polling (для разработки) или webhook (для продакшена)
        if os.getenv('RENDER'):
            # На Render используем webhook
            from telegram.ext import MessageHandler, filters
            application.run_webhook(
                listen="0.0.0.0",
                port=int(os.getenv('PORT', 3000)),
                url_path=self.token,
                webhook_url=f"{os.getenv('WEBHOOK_URL')}/{self.token}"
            )
        else:
            # Для локальной разработки
            application.run_polling()


if __name__ == '__main__':
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN не установлен!")

    bot = FamilyFinanceBot(token)
    bot.run()