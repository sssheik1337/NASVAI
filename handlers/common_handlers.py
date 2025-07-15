import asyncio
import logging
import random
from aiogram import Dispatcher, types, F, Bot
from aiogram.fsm.context import FSMContext
from states import DiaryStates
from keyboards import get_yes_no_keyboard, get_reminder_response_keyboard, get_start_diary_keyboard
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
        "Спасибо большое! Завтра вы получите автоматические напоминания в 8:00, 13:00 и 20:00. "
        "Подскажите, пожалуйста, хотели бы вы получить дополнительные напоминания о заполнении? Очень рекомендуем это сделать!",
        reply_markup=keyboard
    )

async def handle_no_reminders(callback: types.CallbackQuery):
    data = await callback.message.get_data()
    user_name = data.get('user_name', 'Участница')
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"Завтра вы получите напоминания. Отвечать на них никак не нужно, просто продолжайте отвечать на вопрос, на котором остановились. "
        f"Чтобы начать дневник введите команду /start_diary, чтобы ознакомиться еще раз с краткой версией инструкции введите команду /help. "
        f"Удачи с завтрашним заполнением ✨",
        reply_markup=get_start_diary_keyboard()
    )

async def handle_set_reminders(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "Хорошо! Пожалуйста, укажите время для дополнительных напоминаний в 24-часовом формате "
        "(через запятую, если хотите несколько напоминаний). Например, 10:00, 14:30, 21:15"
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
            await message.answer(
                "Извините, пожалуйста, вы ввели время не в том формате. "
                "Укажите его в 24-часовом формате через двоеточие. Например: 07:00 или 12:00"
            )
            return
    if not valid_times:
        await message.answer(
            "Извините, пожалуйста, вы ввели время не в том формате. "
            "Укажите его в 24-часовом формате через двоеточие. Например: 07:00 или 12:00"
        )
        return
    # Добавляем автоматические напоминания
    default_reminders = ["08:00", "13:00", "20:00"]
    all_reminders = list(set(valid_times + default_reminders))
    with sqlite3.connect("research_bot.db") as conn:
        conn.execute(
            "UPDATE participants SET flag = 1, remind_time = ? WHERE chat_id = ?",
            (",".join(all_reminders), message.chat.id)
        )
    await message.answer(
        f"Завтра вы получите напоминания. Отвечать на них никак не нужно, просто продолжайте отвечать на вопрос, на котором остановились. "
        f"Чтобы начать дневник введите команду /start_diary, чтобы ознакомиться еще раз с краткой версией инструкции введите команду /help. "
        f"Удачи с завтрашним заполнением ✨",
        reply_markup=get_start_diary_keyboard()
    )
    await state.clear()

async def background_task(bot: Bot):
    reminder_messages = [
        "Как вы просили, напоминаю про заполнение дневника. Еще раз спасибо, что делитесь своим опытом со мной ✨",
        "Напоминаю про дневник времени ✨ Спасибо большое за ваше участие в исследовании!",
        "По вашей просьбе напоминаю про дневник. Заранее благодарю за ваши записи ✨"
    ]
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
                # Напоминания накануне
                tomorrow = (now + timedelta(days=1)).date()
                tomorrow_weekday = tomorrow.strftime('%A')
                tomorrow_weekday_ru = weekday_translation.get(tomorrow_weekday, tomorrow_weekday)
                cursor.execute('''
                    SELECT chat_id, weekday, weekend, count, name, weekday_date1, weekday_date2, weekend_date1, weekend_date2
                    FROM participants
                    WHERE weekday = ? OR weekend = ?
                ''', (tomorrow_weekday_ru, tomorrow_weekday_ru))
                participants = cursor.fetchall()
                for participant in participants:
                    chat_id, weekday, weekend, count, name, weekday_date1, weekday_date2, weekend_date1, weekend_date2 = participant
                    if (weekday == tomorrow_weekday_ru or weekend == tomorrow_weekday_ru) and count < 2:
                        if now.hour == 20 and now.minute >= 0 and now.minute < 1:
                            alternative_date = weekday_date2 if weekday == tomorrow_weekday_ru else weekend_date2
                            message_text = (
                                f"Добрый вечер, {name}!\n"
                                f"Напоминаю, что завтра ({tomorrow_weekday_ru.lower()}) день, в который вы можете заполнить дневник времени. "
                                f"Подскажите, пожалуйста, вам удобно будет это сделать, или вы хотели бы его заполнить {alternative_date}?"
                            )
                            try:
                                await bot.send_message(chat_id, message_text, reply_markup=get_reminder_response_keyboard())
                                logger.info(f"Отправлено напоминание накануне пользователю {chat_id}")
                            except Exception as e:
                                logger.error(f"Ошибка при отправке напоминания накануне пользователю {chat_id}: {e}")
                        if count == 1 and (weekday_date2 == tomorrow.strftime('%Y-%m-%d') or weekend_date2 == tomorrow.strftime('%Y-%m-%d')):
                            message_text = (
                                f"Добрый вечер, {name}!\n"
                                f"Напоминаю, что завтра ({tomorrow_weekday_ru.lower()}) день, в который вы можете заполнить дневник времени. "
                                f"Завтра вы получите автоматические напоминания в 8:00, 13:00 и 20:00. "
                                f"Подскажите, пожалуйста, хотели бы вы получить дополнительные напоминания о заполнении? Очень рекомендуем это сделать!"
                            )
                            try:
                                await bot.send_message(chat_id, message_text, reply_markup=get_yes_no_keyboard())
                                logger.info(f"Отправлено напоминание для второй даты пользователю {chat_id}")
                            except Exception as e:
                                logger.error(f"Ошибка при отправке напоминания для второй даты пользователю {chat_id}: {e}")
                # Автоматические и пользовательские напоминания
                cursor.execute('''
                    SELECT chat_id, name, remind_time, flag 
                    FROM participants 
                    WHERE flag = 1 AND remind_time IS NOT NULL AND remind_time != ''
                ''')
                users_with_reminders = cursor.fetchall()
                for user in users_with_reminders:
                    chat_id, name, remind_time_str, flag = user
                    cursor.execute('SELECT weekday, weekend, weekday_date1, weekday_date2, weekend_date1, weekend_date2 FROM participants WHERE chat_id = ?', (chat_id,))
                    user_days = cursor.fetchone()
                    if user_days:
                        weekday, weekend, weekday_date1, weekday_date2, weekend_date1, weekend_date2 = user_days
                        if current_date.strftime('%Y-%m-%d') not in [weekday_date1, weekday_date2, weekend_date1, weekend_date2]:
                            continue
                        remind_times = [t.strip() for t in remind_time_str.split(",")]
                        # Автоматические напоминания
                        if current_time == "08:00":
                            try:
                                await bot.send_message(
                                    chat_id,
                                    f"Доброе утро, {name}! Напоминаем, что сегодня день заполнения дневника. "
                                    f"Начните, когда будет удобно, с помощью команды /start_diary. "
                                    f"Ваши записи очень ценны для исследования!"
                                )
                                logger.info(f"Отправлено автоматическое напоминание в 08:00 пользователю {chat_id}")
                            except Exception as e:
                                logger.error(f"Ошибка при отправке автоматического напоминания в 08:00 пользователю {chat_id}: {e}")
                        elif current_time == "13:00":
                            try:
                                await bot.send_message(
                                    chat_id,
                                    f"{name}, добрый день! По возможности заполните промежуточные интервалы дневника. Спасибо большое!"
                                )
                                logger.info(f"Отправлено автоматическое напоминание в 13:00 пользователю {chat_id}")
                            except Exception as e:
                                logger.error(f"Ошибка при отправке автоматического напоминания в 13:00 пользователю {chat_id}: {e}")
                        elif current_time == "20:00":
                            try:
                                await bot.send_message(
                                    chat_id,
                                    f"Добрый вечер, {name}! Завершите, пожалуйста, дневник перед сном. "
                                    f"Чтобы закончить, укажите 'Ночной сон' в ответе на вопрос “Чем вы занимались”. Благодарим за ваше время!"
                                )
                                logger.info(f"Отправлено автоматическое напоминание в 20:00 пользователю {chat_id}")
                            except Exception as e:
                                logger.error(f"Ошибка при отправке автоматического напоминания в 20:00 пользователю {chat_id}: {e}")
                        # Пользовательские напоминания
                        for remind_time in remind_times:
                            if remind_time == current_time and remind_time not in ["08:00", "13:00", "20:00"]:
                                try:
                                    await bot.send_message(
                                        chat_id,
                                        random.choice(reminder_messages)
                                    )
                                    logger.info(f"Отправлено пользовательское напоминание в {remind_time} пользователю {chat_id}")
                                except Exception as e:
                                    logger.error(f"Ошибка при отправке пользовательского напоминания в {remind_time} пользователю {chat_id}: {e}")
                        # Сброс флага в 23:55
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