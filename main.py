import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from database import create_tables
from handlers.survey_handlers import register_handlers as register_survey_handlers
from handlers.diary_handlers import register_handlers as register_diary_handlers
from handlers.feedback_handlers import register_handlers as register_feedback_handlers
from handlers.common_handlers import register_handlers as register_common_handlers, background_task

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),  # Логи в файл
        logging.StreamHandler()  # Логи в консоль
    ]
)
logger = logging.getLogger(__name__)

async def main():
    logger.info("Бот исследования запущен")
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    create_tables()
    register_survey_handlers(dp)
    register_diary_handlers(dp, bot)
    register_feedback_handlers(dp, bot)
    register_common_handlers(dp, bot)
    asyncio.create_task(background_task(bot))
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
    finally:
        logger.info("Бот остановлен")

if __name__ == "__main__":
    asyncio.run(main())