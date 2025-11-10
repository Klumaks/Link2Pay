import threading
from APINIKITKA import app
from Link2Pay import bot
import uvicorn
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_bot():
    """Запуск телеграм бота"""
    try:
        logger.info("🤖 Starting Telegram Bot...")
        bot.infinity_polling()
    except Exception as e:
        logger.error(f"Bot error: {e}")

def run_api():
    """Запуск FastAPI"""
    try:
        logger.info("🚀 Starting FastAPI on http://193.33.153.154:8000")
        uvicorn.run(app, host="host", port="port3", log_level="info")
    except Exception as e:
        logger.error(f"API error: {e}")

if __name__ == '__main__':
    # Запускаем бота в отдельном потоке
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Запускаем API в главном потоке
    run_api()
