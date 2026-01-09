import requests

TOKEN = "8419019535:AAHmqt0z3hX-pCH0Thi3xt8XwAuXtc-0azQ"
WEBHOOK_URL = "https://family-finance-bot-ccdb.onrender.com/webhook"

response = requests.post(
    f"https://api.telegram.org/bot{TOKEN}/setWebhook",
    json={
        "url": WEBHOOK_URL,
        "max_connections": 100,
        "allowed_updates": ["message", "callback_query"]
    }
)

print("Статус:", response.status_code)
print("Ответ:", response.json())