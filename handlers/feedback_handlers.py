import logging
import sqlite3
from aiogram import Dispatcher, types, F, Bot
from aiogram.fsm.context import FSMContext
from states import DiaryStates
from config import GROUP_ID
import pytz
from datetime import datetime

logger = logging.getLogger(__name__)

async def process_feedback_1(message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    worksheet = data['worksheet']
    username_to_find = data['username_to_find']
    if message.voice:
        caption = (f"Ответ на вопрос 1 от @{message.from_user.username or 'нет username'}\n"
                   f"Время: {datetime.now(pytz.timezone('Europe/Moscow')).strftime('%Y-%m-%d %H:%M')}")
        await bot.send_voice(chat_id=GROUP_ID, voice=message.voice.file_id, caption=caption)
        try:
            cell = worksheet.find(username_to_find)
            last_col = len(worksheet.row_values(cell.row))
            worksheet.update_cell(cell.row, last_col + 1, "Ответ на вопрос 1: [голосовое сообщение]")
            logger.info("Ответ на вопрос 1 сохранен как голосовое сообщение")
        except Exception as e:
            logger.error(f"Ошибка при сохранении ответа на вопрос 1: {e}")
    else:
        try:
            cell = worksheet.find(username_to_find)
            last_col = len(worksheet.row_values(cell.row))
            worksheet.update_cell(cell.row, last_col + 1, "Ответ на вопрос 1: " + message.text)
            logger.info("Ответ на вопрос 1 сохранен как текст")
        except Exception as e:
            logger.error(f"Ошибка при сохранении ответа на вопрос 1: {e}")
    await message.answer(
        "Спасибо большое за ответ! Опишите, пожалуйста, как изменилось ваше представление "
        "о том, как вы используете время, после ведения дневника?"
    )
    await state.set_state(DiaryStates.FEEDBACK_QUESTION_2)

async def process_feedback_2(message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    worksheet = data['worksheet']
    username_to_find = data['username_to_find']
    if message.voice:
        caption = (f"Ответ на вопрос 2 от @{message.from_user.username or 'нет username'}\n"
                   f"Время: {datetime.now(pytz.timezone('Europe/Moscow')).strftime('%Y-%m-%d %H:%M')}")
        await bot.send_voice(chat_id=GROUP_ID, voice=message.voice.file_id, caption=caption)
        try:
            cell = worksheet.find(username_to_find)
            last_col = len(worksheet.row_values(cell.row))
            worksheet.update_cell(cell.row, last_col + 1, "Ответ на вопрос 2: [голосовое сообщение]")
            logger.info("Ответ на вопрос 2 сохранен как голосовое сообщение")
        except Exception as e:
            logger.error(f"Ошибка при сохранении ответа на вопрос 2: {e}")
    else:
        try:
            cell = worksheet.find(username_to_find)
            last_col = len(worksheet.row_values(cell.row))
            worksheet.update_cell(cell.row, last_col + 1, "Ответ на вопрос 2: " + message.text)
            logger.info("Ответ на вопрос 2 сохранен как текст")
        except Exception as e:
            logger.error(f"Ошибка при сохранении ответа на вопрос 2: {e}")
    await message.answer(
        "И финально, поделитесь, пожалуйста, вашими впечатлениями от ведения дневника: "
        "что оказалось удобным, а что вызвало сложности? Было ли для вас это занятие трудным? "
        "Может быть, вы сделали какие-то интересные наблюдения о себе в процессе?"
    )
    await state.set_state(DiaryStates.FEEDBACK_QUESTION_3)

async def process_feedback_3(message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    worksheet = data['worksheet']
    username_to_find = data['username_to_find']
    if message.voice:
        caption = (f"Ответ на вопрос 3 от @{message.from_user.username or 'нет username'}\n"
                   f"Время: {datetime.now(pytz.timezone('Europe/Moscow')).strftime('%Y-%m-%d %H:%M')}")
        await bot.send_voice(chat_id=GROUP_ID, voice=message.voice.file_id, caption=caption)
        try:
            cell = worksheet.find(username_to_find)
            last_col = len(worksheet.row_values(cell.row))
            worksheet.update_cell(cell.row, last_col + 1, "Ответ на вопрос 3: [голосовое сообщение]")
            logger.info("Ответ на вопрос 3 сохранен как голосовое сообщение")
        except Exception as e:
            logger.error(f"Ошибка при сохранении ответа на вопрос 3: {e}")
    else:
        try:
            cell = worksheet.find(username_to_find)
            last_col = len(worksheet.row_values(cell.row))
            worksheet.update_cell(cell.row, last_col + 1, "Ответ на вопрос 3: " + message.text)
            logger.info("Ответ на вопрос 3 сохранен как текст")
        except Exception as e:
            logger.error(f"Ошибка при сохранении ответа на вопрос 3: {e}")
    with sqlite3.connect("research_bot.db") as conn:
        conn.execute('DELETE FROM diary_entries WHERE chat_id = ?', (message.chat.id,))
    await message.answer(
        "Огромное спасибо за ваше время, внимание и искренность при заполнении дневника! "
        "Каждая ваша запись – это ценный вклад в мое исследование. Я знаю, что вести дневник – "
        "это непростая задача, требующая дисциплины и внимания к деталям. Вы прекрасно справились! "
        "Увидимся с вами на интервью✨"
    )
    await state.clear()

def register_handlers(dp: Dispatcher, bot: Bot):
    dp.message.register(process_feedback_1, DiaryStates.FEEDBACK_QUESTION_1)
    dp.message.register(process_feedback_2, DiaryStates.FEEDBACK_QUESTION_2)
    dp.message.register(process_feedback_3, DiaryStates.FEEDBACK_QUESTION_3)