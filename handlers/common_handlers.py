import asyncio
import logging
from aiogram import Dispatcher, types, F, Bot
from aiogram.fsm.context import FSMContext
from states import DiaryStates
from keyboards import get_yes_no_keyboard
from datetime import datetime, timedelta, time
import pytz
import sqlite3

logger = logging.getLogger(__name__)

async def handle_remind_later(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("Хорошо, спасибо большое за ответ. Тогда вернусь к вам позднее ✨")

async def handle_remind_ok(callback: types.CallbackQuery, state: FSMContext):
    keyboard = get_yes_no_keyboard()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "Спасибо большое! Подскажите, пожалуйста, хотели бы вы получить завтра напоминания о заполнении?",
        reply_markup=keyboard
    )

async def handle_no_reminders(callback: types.CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "Поняла! Пожалуйста, пробегитесь еще раз по инструкции по заполнению дневника, "
        "чтобы вспомнить ключевые моменты. Удачи с завтрашним заполнением ✨\n\n"
        "Чтобы приступить к выполнению - введите команду /start_diary"
    )

async def handle_set_reminders(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "Хорошо! Пожалуйста, укажите время для напоминаний в 24-часовом формате "
        "(через запятую, если хотите несколько напоминаний). Например, 08:00, 13:30, 21:15"
    )
    await state.set_state(DiaryStates.WAITING_FOR_REMINDERS)

async def process_reminder_times(message: types.Message, state: FSMContext):
    times = [t.strip() for t in message.text.split(",")]
    valid_times = []
    for time_str in times:
        try:
            datetime.strptime(time_str, "%H:%M").time()
            valid_times.append(time_str)
        except ValueError:
            await message.answer(f"Некорректный формат времени: {time_str}. Пожалуйста, используйте формат ЧЧ:ММ")
            return
    if not valid_times:
        await message.answer("Не указано ни одного корректного времени. Попробуйте еще раз.")
        return
    with sqlite3.connect("research_bot.db") as conn:
        conn.execute(
            "UPDATE participants SET flag = 1, remind_time = ? WHERE chat_id = ?",
            (",".join(valid_times), message.chat.id))
    await message.answer(
        "Отлично! Вы получите напоминания в указанное время. "
        "Пожалуйста, пробегитесь еще раз по инструкции по заполнению дневника, "
        "чтобы вспомнить ключевые моменты. Удачи с завтрашним заполнением ✨\n\n"
        "Чтобы приступить к выполнению - введите команду /start_diary"
    )
    await state.clear()

async def background_task(bot: Bot):
    while True:
        try:
            now = datetime.now(pytz.timezone('Europe/Moscow'))
            current_time = now.strftime("%H:%M")
            current_date = now.date()
            current_weekday = now.strftime('%A')
            weekday_translation = {
                "Monday": "Понедельник", "Tuesday": "Вторник", "Wednesday": "Среда",
                "Thursday": "Четверг", "Friday": "Пятница", "Saturday": "Суббота", "Sunday": "Воскресенье"
            }
            current_weekday_ru = weekday_translation.get(current_weekday, current_weekday)
            with sqlite3.connect("research_bot.db") as conn:
                cursor = conn.cursor()
                tomorrow = (now + timedelta(days=1)).date()
                tomorrow_weekday = tomorrow.strftime('%A')
                tomorrow_weekday_ru = weekday_translation.get(tomorrow_weekday, tomorrow_weekday)
                cursor.execute('''
                    SELECT chat_id, weekday, weekend, count, name 
                    FROM participants
                    WHERE weekday = ? OR weekend = ?
                ''', (tomorrow_weekday_ru, tomorrow_weekday_ru))
                participants = cursor.fetchall()
                for participant in participants:
                    chat_id, weekday, weekend, count, name = participant
                    if (weekday == tomorrow_weekday_ru and count < 2) or (weekend == tomorrow_weekday_ru and count < 2):
                        if now.hour == 20 and now.minute >= 0 and now.minute < 1:
                            keyboard = get_yes_no_keyboard()
                            message_text = (
                                f"Добрый вечер, {name}!\n"
                                f"Напоминаю, что завтра ({tomorrow_weekday_ru.lower()}) день, в который вы можете заполнить дневник времени.\n"
                                "Подскажите, пожалуйста, вам удобно будет это сделать?"
                            )
                            try:
                                await bot.send_message(chat_id, message_text, reply_markup=keyboard)
                                logger.info(f"Отправлено напоминание пользователю {chat_id}")
                            except Exception as e:
                                logger.error(f"Ошибка при отправке сообщения пользователю {chat_id}: {e}")
                cursor.execute('''
                    SELECT chat_id, name, remind_time, flag 
                    FROM participants 
                    WHERE flag = 1 AND remind_time IS NOT NULL AND remind_time != ''
                ''')
                users_with_reminders = cursor.fetchall()
                for user in users_with_reminders:
                    chat_id, name, remind_time_str, flag = user
                    cursor.execute('SELECT weekday, weekend FROM participants WHERE chat_id = ?', (chat_id,))
                    user_days = cursor.fetchone()
                    if user_days:
                        weekday, weekend = user_days
                        if current_weekday_ru not in [weekday, weekend]:
                            continue
                        remind_times = [t.strip() for t in remind_time_str.split(",")]
                        for remind_time in remind_times:
                            if remind_time == current_time:
                                try:
                                    await bot.send_message(
                                        chat_id,
                                        "⏰ Напоминаю про дневник времени ✨\n"
                                        "Спасибо большое за ваше участие в исследовании!\n"
                                        "Для того чтобы начать, отправьте команду /start_diary"
                                    )
                                    logger.info(f"Отправлено напоминание пользователю {chat_id} в {current_time}")
                                except Exception as e:
                                    logger.error(f"Ошибка при отправке напоминания пользователю {chat_id}: {e}")
                        if current_time == "23:55":
                            cursor.execute('UPDATE participants SET flag = 0 WHERE chat_id = ?', (chat_id,))
                            conn.commit()
                            logger.info(f"Сброшен флаг для пользователя {chat_id} в 23:55")
        except Exception as e:
            logger.error(f"Ошибка в фоновой задаче: {e}")
        logger.info("Фоновая задача работает")
        await asyncio.sleep(60)

def register_handlers(dp: Dispatcher, bot: Bot):
    dp.callback_query.register(handle_remind_later, F.data == "remind_later")
    dp.callback_query.register(handle_remind_ok, F.data == "remind_ok")
    dp.callback_query.register(handle_no_reminders, F.data == "no_reminders")
    dp.callback_query.register(handle_set_reminders, F.data == "set_reminders")
    dp.message.register(process_reminder_times, DiaryStates.WAITING_FOR_REMINDERS)