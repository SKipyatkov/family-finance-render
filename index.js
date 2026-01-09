const TelegramBot = require('node-telegram-bot-api');
const express = require('express');

const app = express();
app.use(express.json());

const TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const WEB_APP_URL = process.env.WEB_APP_URL;

console.log('🚀 Бот запускается на Render...');

if (!TOKEN) {
  console.error('❌ ОШИБКА: TELEGRAM_BOT_TOKEN не найден!');
  process.exit(1);
}

const bot = new TelegramBot(TOKEN, { polling: false });

// 🎯 ВЕБХУК
app.post('/webhook', (req, res) => {
  console.log('📨 POST /webhook получен!');

  if (req.body && req.body.message) {
    const msg = req.body.message;
    console.log(`👤 От: ${msg.from.first_name}`);
    console.log(`💬 Текст: "${msg.text}"`);
  }

  res.status(200).send('OK');

  try {
    bot.processUpdate(req.body);
  } catch (err) {
    console.error('Ошибка обработки:', err.message);
  }
});

// 🎯 КОМАНДА /start
bot.onText(/\/start/, (msg) => {
  console.log(`✅ /start от ${msg.from.first_name}`);

  bot.sendMessage(msg.chat.id,
    `Привет, ${msg.from.first_name}! 👋\nБот работает на Render! ✅`
  ).catch(err => console.error('Ошибка отправки:', err.message));
});

// 🩺 Health check
app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    hosting: 'Render.com',
    time: new Date().toISOString()
  });
});

// 🏠 Главная
app.get('/', (req, res) => {
  res.send(`
    <h1>🤖 Бот "Копилка" на Render</h1>
    <p>Статус: <strong>Работает ✅</strong></p>
    <p>Вебхук: POST /webhook</p>
    <p>Telegram: @FamilyFinancee_bot</p>
    <p><a href="/health">Health check</a></p>
  `);
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`✅ Сервер запущен на порту ${PORT}`);
  console.log(`✅ Вебхук: http://localhost:${PORT}/webhook`);
});

module.exports = app;