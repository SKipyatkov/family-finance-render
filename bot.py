import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from database import Database

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
        """Обработчик команды /start"""
        user = update.effective_user
        logger.info(f"User {user.id} started the bot")

        # Регистрируем пользователя
        telegram_id = user.id
        user_name = user.first_name or user.username or f"User_{telegram_id}"

        if not self.db.user_exists(telegram_id):
            self.db.add_user(telegram_id, user.username, user.first_name)
            welcome_msg = f"👋 Привет, {user_name}!\n\nДобро пожаловать в семейный финансовый бот 'Копилка'!"
        else:
            welcome_msg = f"С возвращением, {user_name}! 🏠"

        # Создаем клавиатуру с кнопкой Mini App
        keyboard = [
            [InlineKeyboardButton(
                "📱 Открыть приложение",
                web_app=WebAppInfo(url=f"{self.web_app_url}/?telegram_id={telegram_id}")
            )],
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

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка callback-запросов"""
        query = update.callback_query
        await query.answer()

        data = query.data
        telegram_id = query.from_user.id

        if data == 'reports':
            user = self.db.get_user_by_telegram_id(telegram_id)
            if user:
                report = self.db.get_monthly_report(user['id'])
                await query.edit_message_text(
                    text=f"📊 Отчет за месяц:\n\n"
                         f"💰 Доходы: {report['total_income']} ₽\n"
                         f"🛒 Расходы: {report['total_expense']} ₽\n"
                         f"📈 Баланс: {report['balance']} ₽\n\n"
                         f"Нажмите кнопку ниже для детального отчета:",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            "📱 Подробный отчет",
                            web_app=WebAppInfo(url=f"{self.web_app_url}/?telegram_id={telegram_id}")
                        )
                    ]])
                )

        elif data == 'family':
            user = self.db.get_user_by_telegram_id(telegram_id)
            if user and user.get('family_id'):
                members = self.db.get_family_members(user['family_id'])
                members_text = "\n".join([f"• {m.get('first_name') or m.get('username')}" for m in members])

                await query.edit_message_text(
                    text=f"👨‍👩‍👧‍👦 Ваша семья:\n\n{members_text}\n\n"
                         f"Всего участников: {len(members)}",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            "📱 Управление семьей",
                            web_app=WebAppInfo(url=f"{self.web_app_url}/?telegram_id={telegram_id}")
                        )
                    ]])
                )
            else:
                await query.edit_message_text(
                    text="Вы еще не создали семью. Хотите создать?",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            "📱 Создать семью",
                            web_app=WebAppInfo(url=f"{self.web_app_url}/?telegram_id={telegram_id}")
                        )
                    ]])
                )

    def run(self):
        """Запуск бота"""
        application = Application.builder().token(self.token).build()

        # Регистрация обработчиков
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("help", self.start))
        application.add_handler(CallbackQueryHandler(self.handle_callback))

        # Запуск webhook для Render
        webhook_url = f"{self.web_app_url}/webhook"
        application.run_webhook(
            listen="0.0.0.0",
            port=int(os.getenv('PORT', 5000)),
            url_path=self.token,
            webhook_url=webhook_url
        )


if __name__ == '__main__':
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("❌ ОШИБКА: TELEGRAM_BOT_TOKEN не установлен!")
        exit(1)

    bot = FamilyFinanceBot(token)
    bot.run()