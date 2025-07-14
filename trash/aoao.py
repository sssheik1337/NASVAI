import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import asyncio
import pytz
from datetime import datetime, time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, time, timedelta
from aiogram import F
from aiogram.filters import StateFilter
from aiogram.types import Voice


GROUP_ID = -1002533521039
night_sleep_filter = F.text.lower() == "ночной сон"

# Конфигурация бота
BOT_TOKEN = "7852813577:AAFnSuwykTTwJP70CuKbHhmkyH57n4vz-xo"
DB_FILE = "research_bot.db"
GOOGLE_SHEETS_CREDENTIALS_FILE = "../diaries-461014-26cf812fce8f.json"
SPREADSHEET_ID = "10GLIHybod0JjjbnrJGQydXQWaY4AFzWq2kQBPdMZTo0"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


class SurveyStates(StatesGroup):
    WAITING_FOR_START = State()
    ASKING_NAME = State()
    QUESTION_1_AGE = State()
    QUESTION_2_HUSBAND = State()
    QUESTION_3_CHILDREN_COUNT = State()
    QUESTION_4_CHILD_AGE = State()
    QUESTION_5_FAMILY = State()
    QUESTION_6_INCOME = State()
    QUESTION_7_HELP = State()
    QUESTION_8_LOCATION = State()
    QUESTION_8A_LOCATION_DETAIL = State()
    QUESTION_9_KINDERGARTEN = State()
    QUESTION_10_NANNY = State()
    QUESTION_11_ACTIVITIES = State()
    QUESTION_12_EDUCATION = State()
    QUESTION_13_EDUCATION_DETAILS = State()
    QUESTION_13_EDUCATION_LEVEL = State()
    QUESTION_13_EDUCATION_YEAR = State()
    QUESTION_14_SCHEDULE = State()
    QUESTION_15_FIELD = State()
    QUESTION_16_JOB_CHANGE = State()
    SELECT_WEEKDAY = State()
    SELECT_WEEKEND = State()
    INSTRUCTION_1 = State()
    INSTRUCTION_2 = State()
    INSTRUCTION_3 = State()
    INSTRUCTION_4 = State()
    FINISHED = State()


# Добавим новые состояния
class DiaryStates(StatesGroup):
    WAITING_FOR_WAKE_UP = State()
    RECORDING_ACTIVITY = State()
    RECORDING_LOCATION = State()
    RECORDING_LOCATION_OTHER = State()
    RECORDING_COMPANIONS = State()
    RECORDING_COMPANIONS_OTHER = State()
    ASKING_ADD_COMPANION = State()
    WAITING_FOR_REMINDERS = State()
    FEEDBACK_QUESTION_1 = State()
    FEEDBACK_QUESTION_2 = State()
    FEEDBACK_QUESTION_3 = State()
    # Новое состояние


async def background_task():
    while True:
        try:
            now = datetime.now(pytz.timezone('Europe/Moscow'))
            current_time = now.strftime("%H:%M")
            current_date = now.date()
            current_weekday = now.strftime('%A')

            weekday_translation = {
                "Monday": "Понедельник",
                "Tuesday": "Вторник",
                "Wednesday": "Среда",
                "Thursday": "Четверг",
                "Friday": "Пятница",
                "Saturday": "Суббота",
                "Sunday": "Воскресенье"
            }
            current_weekday_ru = weekday_translation.get(current_weekday, current_weekday)

            with sqlite3.connect(DB_FILE) as conn:
                cursor = conn.cursor()

                # 1. Проверка на напоминание о завтрашнем дне (существующая логика)
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
                    if (weekday == tomorrow_weekday_ru and count < 2) or \
                            (weekend == tomorrow_weekday_ru and count < 2):
                        if now.hour == 20 and now.minute >= 00 and now.minute < 1:
                            keyboard = InlineKeyboardMarkup(
                                inline_keyboard=[
                                    [InlineKeyboardButton(text="Удобно", callback_data="remind_ok")],
                                    [InlineKeyboardButton(text="В другой день", callback_data="remind_later")]
                                ]
                            )
                            message_text = (
                                f"Добрый вечер, {name}!\n"
                                f"Напоминаю, что завтра ({tomorrow_weekday_ru.lower()}) день, в который вы можете заполнить дневник времени.\n"
                                "Подскажите, пожалуйста, вам удобно будет это сделать?"
                            )
                            try:
                                await bot.send_message(chat_id, message_text, reply_markup=keyboard)
                                print(f"Отправлено напоминание пользователю {chat_id}")
                            except Exception as e:
                                print(f"Ошибка при отправке сообщения пользователю {chat_id}: {e}")

                # 2. Новая логика: напоминания в указанное время и сброс флага в 23:55
                cursor.execute('''
                    SELECT chat_id, name, remind_time, flag 
                    FROM participants 
                    WHERE flag = 1 AND remind_time IS NOT NULL AND remind_time != ''
                ''')
                users_with_reminders = cursor.fetchall()

                for user in users_with_reminders:
                    chat_id, name, remind_time_str, flag = user

                    # Проверяем, совпадает ли текущий день с выбранным днем пользователя
                    cursor.execute('''
                        SELECT weekday, weekend 
                        FROM participants 
                        WHERE chat_id = ?
                    ''', (chat_id,))
                    user_days = cursor.fetchone()

                    if user_days:
                        weekday, weekend = user_days
                        if current_weekday_ru not in [weekday, weekend]:
                            continue  # не сегодняшний день пользователя

                        # Обработка напоминаний
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
                                    print(f"Отправлено напоминание пользователю {chat_id} в {current_time}")
                                except Exception as e:
                                    print(f"Ошибка при отправке напоминания пользователю {chat_id}: {e}")

                        # Сброс флага в 23:55
                        if current_time == "23:55":
                            cursor.execute('''
                                UPDATE participants 
                                SET flag = 0 
                                WHERE chat_id = ?
                            ''', (chat_id,))
                            conn.commit()
                            print(f"Сброшен флаг для пользователя {chat_id} в 23:55")

        except Exception as e:
            print(f"Ошибка в фоновой задаче: {e}")
        print("работаем")
        await asyncio.sleep(60)  # Проверяем каждые 15 секунд


@dp.callback_query(F.data == "remind_later")
async def handle_remind_later(callback: types.CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("Хорошо, спасибо большое за ответ. Тогда вернусь к вам позднее ✨")

@dp.callback_query(F.data == "remind_ok")
async def handle_remind_ok(callback: types.CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Да", callback_data="set_reminders")],
            [InlineKeyboardButton(text="Нет", callback_data="no_reminders")]
        ]
    )
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "Спасибо большое! Подскажите, пожалуйста, хотели бы вы получить завтра напоминания о заполнении?",
        reply_markup=keyboard
    )

@dp.callback_query(F.data == "no_reminders")
async def handle_no_reminders(callback: types.CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "Поняла! Пожалуйста, пробегитесь еще раз по инструкции по заполнению дневника, "
        "чтобы вспомнить ключевые моменты. Удачи с завтрашним заполнением ✨\n\n"
        "Чтобы приступить к выполнению - введите команду /start_diary"
    )



@dp.callback_query(F.data == "remind_later")
async def handle_remind_later(callback: types.CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("Хорошо, спасибо большое за ответ. Тогда вернусь к вам позднее ✨")

@dp.callback_query(F.data == "remind_ok")
async def handle_remind_ok(callback: types.CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Да", callback_data="set_reminders")],
            [InlineKeyboardButton(text="Нет", callback_data="no_reminders")]
        ]
    )
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "Спасибо большое! Подскажите, пожалуйста, хотели бы вы получить завтра напоминания о заполнении?",
        reply_markup=keyboard
    )

@dp.callback_query(F.data == "no_reminders")
async def handle_no_reminders(callback: types.CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "Поняла! Пожалуйста, пробегитесь еще раз по инструкции по заполнению дневника, "
        "чтобы вспомнить ключевые моменты. Удачи с завтрашним заполнением ✨\n\n"
        "Чтобы приступить к выполнению - введите команду /start_diary"
    )

@dp.callback_query(F.data == "set_reminders")
async def handle_set_reminders(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "Хорошо! Пожалуйста, укажите время для напоминаний в 24-часовом формате "
        "(через запятую, если хотите несколько напоминаний). Например, 08:00, 13:30, 21:15"
    )
    await state.set_state(DiaryStates.WAITING_FOR_REMINDERS)


@dp.message(DiaryStates.WAITING_FOR_REMINDERS)
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

    # Сохраняем времена напоминаний в базу данных
    with sqlite3.connect(DB_FILE) as conn:
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





# Обновленная функция для создания клавиатуры местоположения
def get_location_buttons():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="У себя дома", callback_data="loc_home")],
            [InlineKeyboardButton(text="У кого-то другого дома", callback_data="loc_other_home")],
            [InlineKeyboardButton(text="На работе", callback_data="loc_work")],
            [InlineKeyboardButton(text="В пути", callback_data="loc_transport")],
            [InlineKeyboardButton(text="На улице", callback_data="loc_outside")],
            [InlineKeyboardButton(text="В больнице", callback_data="loc_hospital")],
            [InlineKeyboardButton(text="В магазине", callback_data="loc_shop")],
            [InlineKeyboardButton(text="Другое", callback_data="loc_other")]
        ]
    )


# Обновленная функция для создания клавиатуры компании
def get_companions_buttons():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Я была одна", callback_data="comp_alone")],
            [InlineKeyboardButton(text="Муж", callback_data="comp_husband")],
            [InlineKeyboardButton(text="Ребенок", callback_data="comp_child")],
            [InlineKeyboardButton(text="Родители/родители мужа", callback_data="comp_parents")],
            [InlineKeyboardButton(text="Другие родственники", callback_data="comp_relatives")],
            [InlineKeyboardButton(text="Друзья", callback_data="comp_friends")],
            [InlineKeyboardButton(text="Коллеги", callback_data="comp_colleagues")],
            [InlineKeyboardButton(text="Другие люди", callback_data="comp_others")]
        ]
    )


# Обновленный обработчик вопроса о местоположении
@dp.message(DiaryStates.RECORDING_ACTIVITY)
async def process_activity(message: types.Message, state: FSMContext):
    user_answer = message.text.strip()

    if user_answer.lower() == "ночной сон":
        await finish_diary(message, state)
        return

    await state.update_data(current_activity=user_answer)
    await message.answer(
        "2. Где вы находились в это время?",
        reply_markup=get_location_buttons()
    )
    await state.set_state(DiaryStates.RECORDING_LOCATION)


# Обработчик выбора местоположения
@dp.callback_query(F.data.startswith("loc_"), DiaryStates.RECORDING_LOCATION)
async def process_location(callback: types.CallbackQuery, state: FSMContext):
    location_map = {
        "loc_home": "У себя дома",
        "loc_other_home": "У кого-то другого дома",
        "loc_work": "На работе",
        "loc_transport": "В пути",
        "loc_outside": "На улице",
        "loc_hospital": "В больнице",
        "loc_shop": "В магазине",
        "loc_other": "Другое"
    }

    location = location_map[callback.data]

    if callback.data == "loc_other":
        await callback.message.answer("Пожалуйста, укажите, где вы находились:")
        await state.set_state(DiaryStates.RECORDING_LOCATION_OTHER)
    else:
        await state.update_data(current_location=location)
        await callback.message.answer(
            "3. С кем вы были в это время?",
            reply_markup=get_companions_buttons()
        )
        await state.set_state(DiaryStates.RECORDING_COMPANIONS)
    await callback.message.edit_reply_markup(reply_markup=None)


# Обработчик ручного ввода местоположения
@dp.message(DiaryStates.RECORDING_LOCATION_OTHER)
async def process_location_other(message: types.Message, state: FSMContext):
    await state.update_data(current_location=f"Другое: {message.text.strip()}")
    await message.answer(
        "3. С кем вы были в это время?",
        reply_markup=get_companions_buttons()
    )
    await state.set_state(DiaryStates.RECORDING_COMPANIONS)


# Обработчик выбора компании
@dp.callback_query(F.data.startswith("comp_"), DiaryStates.RECORDING_COMPANIONS)
async def process_companions(callback: types.CallbackQuery, state: FSMContext):
    companion_map = {
        "comp_alone": "Я была одна",
        "comp_husband": "Муж",
        "comp_child": "Ребенок",
        "comp_parents": "Родители/родители мужа",
        "comp_relatives": "Другие родственники",
        "comp_friends": "Друзья",
        "comp_colleagues": "Коллеги",
        "comp_others": "Другие люди"
    }

    companion = companion_map[callback.data]

    if callback.data == "comp_others":
        await callback.message.answer("Пожалуйста, укажите, с кем вы были:")
        await state.set_state(DiaryStates.RECORDING_COMPANIONS_OTHER)
    else:
        data = await state.get_data()
        current_companions = data.get('current_companions', [])
        current_companions.append(companion)
        await state.update_data(current_companions=current_companions)

        # Спрашиваем, хочет ли пользователь добавить еще кого-то
        await callback.message.answer(
            f"Вы выбрали: {', '.join(current_companions)}\n"
            "Хотите добавить еще кого-то?",
            reply_markup=get_yes_no_keyboard()
        )
        await state.set_state(DiaryStates.ASKING_ADD_COMPANION)

    await callback.message.edit_reply_markup(reply_markup=None)


# Обработчик ручного ввода компании
@dp.message(DiaryStates.RECORDING_COMPANIONS_OTHER)
async def process_companions_other(message: types.Message, state: FSMContext):
    data = await state.get_data()
    current_companions = data.get('current_companions', [])
    current_companions.append(f"Другие: {message.text.strip()}")
    await state.update_data(current_companions=current_companions)

    await message.answer(
        f"Вы выбрали: {', '.join(current_companions)}\n"
        "Хотите добавить еще кого-то?",
        reply_markup=get_yes_no_keyboard()
    )
    await state.set_state(DiaryStates.ASKING_ADD_COMPANION)


# Обработчик вопроса о добавлении еще кого-то
@dp.callback_query(F.data.in_(["yes", "no"]), DiaryStates.ASKING_ADD_COMPANION)
async def process_add_companion(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "yes":
        await callback.message.answer(
            "Кого еще добавить?",
            reply_markup=get_companions_buttons()
        )
        await state.set_state(DiaryStates.RECORDING_COMPANIONS)
    else:
        data = await state.get_data()
        current_companions = data.get('current_companions', [])
        companions_str = ", ".join(current_companions)

        # Сохраняем данные и переходим к следующему интервалу
        now = datetime.now(pytz.timezone('Europe/Moscow'))
        now_full = now.strftime("%Y-%m-%d %H:%M:%S")

        with sqlite3.connect(DB_FILE) as conn:
            conn.execute('''
                INSERT INTO diary_entries 
                (chat_id, username, entry_date, timestamp, time_period, activity, location, companions)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                         (
                             callback.message.chat.id,
                             callback.from_user.username,
                             now.strftime('%Y-%m-%d'),
                             now_full,
                             f"{data['current_period_start']}-{data['current_period_end']}",
                             data.get('current_activity', ''),
                             data.get('current_location', ''),
                             companions_str
                         )
                         )

        # Обновляем временной интервал
        current_end = datetime.strptime(data['current_period_end'], "%H:%M").time()
        next_start = current_end
        next_end = (datetime.combine(now.date(), next_start) + timedelta(minutes=20)).time()

        await state.update_data(
            current_period_start=next_start.strftime("%H:%M"),
            current_period_end=next_end.strftime("%H:%M"),
            current_companions=[]
        )

        # Задаем вопрос о следующем периоде
        await ask_activity_question(callback.message, state)

    await callback.message.edit_reply_markup(reply_markup=None)


    # Проверяем, был ли callback уже обработан другими обработчиками
    if not callback.message:
        return

    # Получаем текст кнопки из callback_data
    button_text = None
    for row in callback.message.reply_markup.inline_keyboard:
        for button in row:
            if button.callback_data == callback.data:
                button_text = button.text
                break
        if button_text:
            break

    if button_text:
        await callback.answer(f"Вы выбрали: {button_text}")
    else:
        await callback.answer("Неизвестная кнопка")
# Добавим обработчик команды /start_diary
@dp.message(Command("start_diary"))
async def cmd_start_diary(message: types.Message, state: FSMContext):
    await message.answer(
        "Начинаем ведение дневника времени. Пожалуйста, укажите время вашего пробуждения "
        "в 24-часовом формате (например, 07:30 или 09:45):"
    )
    await state.set_state(DiaryStates.WAITING_FOR_WAKE_UP)


# Обработчик времени пробуждения
@dp.message(DiaryStates.WAITING_FOR_WAKE_UP)
async def process_wake_up_time(message: types.Message, state: FSMContext):
    try:
        # Проверяем формат времени
        wake_up_time = datetime.strptime(message.text.strip(), "%H:%M").time()
        now = datetime.now(pytz.timezone('Europe/Moscow'))

        # Определяем первый 20-минутный интервал
        start_minute = (wake_up_time.minute // 20) * 20
        current_period_start = wake_up_time.replace(minute=start_minute, second=0)
        current_period_end = (datetime.combine(now.date(), current_period_start) + timedelta(minutes=20)).time()

        # Сохраняем данные в state
        await state.update_data(
            diary_entries=[],
            current_period_start=current_period_start.strftime("%H:%M"),
            current_period_end=current_period_end.strftime("%H:%M"),
            wake_up_time=wake_up_time.strftime("%H:%M"),
            diary_start_time=now.strftime("%Y-%m-%d %H:%M:%S")
        )

        # Задаем первый вопрос
        await ask_activity_question(message, state)

    except ValueError:
        await message.answer("Пожалуйста, введите время в формате ЧЧ:MM (например, 07:30)")


# Функция для вопроса о деятельности
async def ask_activity_question(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await message.answer(
        f"📝 Период времени: {data['current_period_start']}-{data['current_period_end']}\n\n"
        "1. Чем вы занимались в это время? (Опишите все ваши действия, включая параллельные)"
    )
    await state.set_state(DiaryStates.RECORDING_ACTIVITY)


# Обработчик ответа на вопрос о деятельности
@dp.message(DiaryStates.RECORDING_ACTIVITY)
async def process_activity(message: types.Message, state: FSMContext):
    user_answer = message.text.strip()

    # Проверяем, не хочет ли пользователь закончить дневник
    if user_answer.lower() == "ночной сон":
        await finish_diary(message, state)
        return

    await state.update_data(current_activity=user_answer)
    await message.answer(
        "2. Где вы находились в это время? (Можно выбрать несколько вариантов)\n\n"
        "Примеры: дома, на работе, в транспорте, в магазине, на прогулке и т.д."
    )
    await state.set_state(DiaryStates.RECORDING_LOCATION)


# Обработчик ответа на вопрос о местоположении
@dp.message(DiaryStates.RECORDING_LOCATION)
async def process_location(message: types.Message, state: FSMContext):
    await state.update_data(current_location=message.text.strip())
    await message.answer(
        "3. С кем вы были в это время? (Можно выбрать несколько вариантов)\n\n"
        "Примеры: одна, с ребенком, с мужем, с коллегами, с друзьями и т.д."
    )
    await state.set_state(DiaryStates.RECORDING_COMPANIONS)


# Обработчик ответа на вопрос о компании
@dp.message(DiaryStates.RECORDING_COMPANIONS)
async def process_companions(message: types.Message, state: FSMContext):
    data = await state.get_data()
    now = datetime.now(pytz.timezone('Europe/Moscow'))
    now_full = now.strftime("%Y-%m-%d %H:%M:%S")

    if message.text.strip().lower() == "ночной сон":
        await finish_diary(message, state)
        return

    # Сохраняем текущую запись
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute('''
            INSERT INTO diary_entries 
            (chat_id, username, entry_date, timestamp, time_period, activity, location, companions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                message.chat.id,
                message.from_user.username,
                now.strftime('%Y-%m-%d'),
                now_full,
                f"{data['current_period_start']}-{data['current_period_end']}",
                data.get('current_activity', ''),
                data.get('current_location', ''),
                message.text.strip()
            )
        )

    # Обновляем временной интервал на следующий 20-минутный период
    current_end = datetime.strptime(data['current_period_end'], "%H:%M").time()
    next_start = current_end
    next_end = (datetime.combine(now.date(), next_start) + timedelta(minutes=20)).time()

    await state.update_data(
        current_period_start=next_start.strftime("%H:%M"),
        current_period_end=next_end.strftime("%H:%M")
    )

    # Задаем вопрос о следующем периоде
    await ask_activity_question(message, state)


async def finish_diary(message: types.Message, state: FSMContext):
    # Получаем данные из базы данных для этого пользователя
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT time_period, activity, location, companions, timestamp, username 
            FROM diary_entries 
            WHERE chat_id = ? 
            ORDER BY timestamp''',
                       (message.chat.id,)
                       )
        entries = cursor.fetchall()

        # Получаем имя пользователя и count из participants
        cursor.execute('SELECT name, count FROM participants WHERE chat_id = ?', (message.chat.id,))
        user_data = cursor.fetchone()
        user_name = user_data[0] if user_data else "Неизвестный пользователь"
        current_count = user_data[1] if user_data else 0

        # Увеличиваем счетчик заполнений на 1
        new_count = current_count + 1
        cursor.execute('''
            UPDATE participants 
            SET count = ? 
            WHERE chat_id = ?''',
                       (new_count, message.chat.id)
                       )
        conn.commit()

    # Формируем отчет
    report = []
    for entry in entries:
        time_period, activity, location, companions, timestamp, username = entry
        report_line = (
            f"В промежуток [{time_period}] пользователь [{username or 'нет username'} - {user_name}] "
            f"делал [{activity}] в локации [{location}] с компанией [{companions}]. "
            f"Запись оставил в [{timestamp}]."
        )
        report.append(report_line)

    # Объединяем все строки отчета
    full_report = "\n".join(report)

    # Выводим отчет в консоль (как просили)
    print("\n" + "=" * 50)
    print("ОТЧЕТ О ДЕЯТЕЛЬНОСТИ ПОЛЬЗОВАТЕЛЯ:")
    print(full_report)
    print("=" * 50 + "\n")

    # Сохраняем отчет в Google Таблицу
    try:
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            GOOGLE_SHEETS_CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        worksheet = spreadsheet.sheet1

        # Находим строку с username пользователя (с @)
        username_to_find = f"@{message.from_user.username}" if message.from_user.username else None

        if new_count == 2:
            # Если это второе заполнение, задаем дополнительные вопросы
            await state.set_data({'worksheet': worksheet, 'username_to_find': username_to_find})
            await message.answer(
                "Далее, я попрошу вас ответить на несколько вопросов об опыте заполнения дневника. "
                "Вы можете отвечать в свободной форме.\n\n"
                "Первый вопрос: отражает ли ваш дневник привычный для вас распорядок, или эти дни "
                "чем-то выделялись из вашей обычной рутины? Расскажите, пожалуйста, поподробней."
            )
            await state.set_state(DiaryStates.FEEDBACK_QUESTION_1)
            return
        else:
            if username_to_find:
                try:
                    cell = worksheet.find(username_to_find)
                    # Добавляем отчет в последний столбец найденной строки
                    last_col = len(worksheet.row_values(cell.row))
                    worksheet.update_cell(cell.row, last_col + 1, full_report)
                    print(f"Отчет успешно добавлен в строку {cell.row}")
                except gspread.exceptions.CellNotFound:
                    print("Пользователь не найден в таблице")
            else:
                print("Username не найден, невозможно добавить отчет")

    except Exception as e:
        print(f"Ошибка при сохранении в Google Sheets: {e}")

    # Очищаем записи дневника для этого пользователя
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute('DELETE FROM diary_entries WHERE chat_id = ?', (message.chat.id,))

    await message.answer(
        "Дневник времени успешно сохранен! Спасибо за ваши записи.\n"
        "Вы можете продолжить в другой раз, снова используя команду /start_diary."
    )
    await state.clear()





def get_start_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Начать", callback_data="start_survey")]
        ]
    )


def get_yes_no_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Да", callback_data="yes"),
             InlineKeyboardButton(text="Нет", callback_data="no")]
        ]
    )


def get_income_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Высокий", callback_data="income_high")],
            [InlineKeyboardButton(text="Выше среднего", callback_data="income_above_avg")],
            [InlineKeyboardButton(text="Средний", callback_data="income_avg")],
            [InlineKeyboardButton(text="Ниже среднего", callback_data="income_below_avg")],
            [InlineKeyboardButton(text="Низкий", callback_data="income_low")]
        ]
    )

def get_understand_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Понятно", callback_data="understand")]
        ]
    )

def get_location_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Москва", callback_data="location_moscow")],
            [InlineKeyboardButton(text="Московская область", callback_data="location_mo")]
        ]
    )


def get_schedule_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Полный день (фикс)", callback_data="schedule_full_fixed")],
            [InlineKeyboardButton(text="Полный день (гибкий)", callback_data="schedule_full_flex")],
            [InlineKeyboardButton(text="Неполный день", callback_data="schedule_part")],
            [InlineKeyboardButton(text="Удалённо (по графику)", callback_data="schedule_remote")],
            [InlineKeyboardButton(text="Временная/проектная", callback_data="schedule_temp")],
            [InlineKeyboardButton(text="Не работаю", callback_data="schedule_no")]
        ]
    )


def get_weekdays_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Понедельник", callback_data="day_monday")],
            [InlineKeyboardButton(text="Вторник", callback_data="day_tuesday")],
            [InlineKeyboardButton(text="Среда", callback_data="day_wednesday")],
            [InlineKeyboardButton(text="Четверг", callback_data="day_thursday")],
            [InlineKeyboardButton(text="Пятница", callback_data="day_friday")]
        ]
    )


def get_weekend_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Суббота", callback_data="day_saturday")],
            [InlineKeyboardButton(text="Воскресенье", callback_data="day_sunday")]
        ]
    )


def init_google_sheets():
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        GOOGLE_SHEETS_CREDENTIALS_FILE, scope)
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_ID).sheet1


def create_tables():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id BIGINT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                username TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                weekday TEXT,
                weekend TEXT,
                weekday_date1 TEXT,
                weekday_date2 TEXT,
                weekend_date1 TEXT,
                weekend_date2 TEXT,
                remind_time TEXT,
                flag INT DEFAUlT 0,
                count INTEGER DEFAULT 0
            )''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS survey_answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id BIGINT NOT NULL,
                question INTEGER NOT NULL,
                answer TEXT NOT NULL,
                FOREIGN KEY(chat_id) REFERENCES participants(chat_id)
            )''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS diary_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id BIGINT NOT NULL,
                username TEXT,
                entry_date TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                time_period TEXT NOT NULL,
                activity TEXT,
                location TEXT,
                companions TEXT,
                FOREIGN KEY(chat_id) REFERENCES participants(chat_id)
            )''')

async def save_answer(chat_id: int, question_num: int, answer: str):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute(
                '''INSERT INTO survey_answers 
                (chat_id, question, answer) 
                VALUES (?, ?, ?)''',
                (chat_id, question_num, answer)
            )
    except Exception as e:
        print(f"Ошибка сохранения ответа: {e}")


async def save_to_google_sheets(chat_id: int):
    try:
        try:
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            creds = ServiceAccountCredentials.from_json_keyfile_name(
                GOOGLE_SHEETS_CREDENTIALS_FILE, scope)
            client = gspread.authorize(creds)

            try:
                spreadsheet = client.open_by_key(SPREADSHEET_ID)
                worksheet = spreadsheet.sheet1
            except gspread.SpreadsheetNotFound:
                print(f"Таблица с ID {SPREADSHEET_ID} не найдена")
                return False
            except Exception as e:
                print(f"Ошибка при открытии таблицы: {e}")
                return False
        except Exception as e:
            print(f"Ошибка авторизации в Google API: {e}")
            return False

        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT name, username FROM participants WHERE chat_id = ?',
                (chat_id,)
            )
            user_data = cursor.fetchone()
            cursor.execute(
                'SELECT question, answer FROM survey_answers WHERE chat_id = ? ORDER BY question',
                (chat_id,)
            )
            answers = cursor.fetchall()

        if not user_data or not answers:
            print("Не найдены данные пользователя или ответы")
            return False

        name, username = user_data
        row_data = [
            str(datetime.now()),
            name,
            f"@{username}" if username else "",
            *[answer for _, answer in sorted(answers, key=lambda x: x[0])]
        ]

        try:
            worksheet.append_row(row_data)
            print("Данные успешно сохранены в Google Sheets")
            return True
        except Exception as e:
            print(f"Ошибка при добавлении строки: {e}")
            return False

    except Exception as e:
        print(f"Общая ошибка при сохранении в Google Sheets: {e}")
        return False


@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    welcome_text = """
Здравствуйте✨

Большое спасибо вам за участие в моем исследовании, посвященном возвращению женщин после декретного отпуска на работу. Все данные, которые вы здесь предоставите, будут полностью анонимными, а в итоговой исследовательской работе будут указаны в обобщенном виде.

Спасибо за ваш вклад в развитие социальных исследований! Ваши ответы помогут создать более эффективные программы поддержки для женщин в аналогичной ситуации.

Для старта отправьте "Начать".
    """
    await message.answer(welcome_text, reply_markup=get_start_keyboard())
    await state.set_state(SurveyStates.WAITING_FOR_START)


@dp.callback_query(F.data == "start_survey", SurveyStates.WAITING_FOR_START)
async def handle_start_survey(callback: types.CallbackQuery, state: FSMContext):
    # Убираем кнопку "Начать" из сообщения
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("Подскажите, пожалуйста, как я могу к вам обращаться?")
    await state.set_state(SurveyStates.ASKING_NAME)


@dp.message(SurveyStates.ASKING_NAME)
async def process_user_name(message: types.Message, state: FSMContext):
    user_name = message.text.strip()
    await state.update_data(user_name=user_name)

    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute(
                '''INSERT OR REPLACE INTO participants 
                (chat_id, name, username) 
                VALUES (?, ?, ?)''',
                (message.chat.id, user_name, message.from_user.username)
            )
    except Exception as e:
        print(f"Ошибка сохранения данных: {e}")
        await message.answer("Произошла ошибка при сохранении данных. Пожалуйста, попробуйте позже.")
        return

    await message.answer(
        f"{user_name}, в качестве первого этапа, предлагаю вам пройти короткую анкету. "
        f"Она состоит из 16 вопросов о вашей семье, образовании, занятости и поддержке в уходе за ребенком. "
        f"Заполнение займет около 5 минут. Это поможет мне узнать о вас чуть-чуть побольше, а также облегчит дальнейшие интервью."
        f"\n\n1. Сколько вам лет?"
    )
    await state.set_state(SurveyStates.QUESTION_1_AGE)


@dp.message(SurveyStates.QUESTION_1_AGE)
async def process_question_1(message: types.Message, state: FSMContext):
    age = message.text.strip()
    await save_answer(message.chat.id, 1, age)
    await message.answer("2. Есть ли у вас муж?", reply_markup=get_yes_no_keyboard())
    await state.set_state(SurveyStates.QUESTION_2_HUSBAND)


@dp.callback_query(F.data.in_(["yes", "no"]), SurveyStates.QUESTION_2_HUSBAND)
async def process_question_2(callback: types.CallbackQuery, state: FSMContext):
    answer = "Да" if callback.data == "yes" else "Нет"
    await callback.message.answer(f"Вы выбрали: {answer}")  # Добавлено
    await save_answer(callback.message.chat.id, 2, answer)
    # Убираем кнопки из сообщения
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("3. Сколько у вас детей?")
    await state.set_state(SurveyStates.QUESTION_3_CHILDREN_COUNT)


@dp.message(SurveyStates.QUESTION_3_CHILDREN_COUNT)
async def process_question_3(message: types.Message, state: FSMContext):
    count = message.text.strip()
    await save_answer(message.chat.id, 3, count)
    await message.answer("4. Сколько лет вашему ребенку?")
    await state.set_state(SurveyStates.QUESTION_4_CHILD_AGE)


@dp.message(SurveyStates.QUESTION_4_CHILD_AGE)
async def process_question_4(message: types.Message, state: FSMContext):
    age = message.text.strip()
    await save_answer(message.chat.id, 4, age)
    await message.answer("5. Опишите состав вашей семьи (тех, кто живет с вами в одном доме).")
    await state.set_state(SurveyStates.QUESTION_5_FAMILY)


@dp.message(SurveyStates.QUESTION_5_FAMILY)
async def process_question_5(message: types.Message, state: FSMContext):
    family = message.text.strip()
    await save_answer(message.chat.id, 5, family)
    await message.answer("6. Как вы оцениваете доход своей семьи?"
                         "\n●	Высокий - свободно покрываем все расходы, включая путешествия и крупные покупки, откладываем сбережения"
                        "\n●	Выше среднего - хватает на комфортную жизнь и развлечения, но дорогие покупки требуют накоплений"
"\n●	Средний - средств достаточно на основные нужды (еда, жилье, одежда), но на дополнительные траты остаётся мало"
"\n●	Ниже среднего - денег хватает только на самое необходимое, приходится строго экономить"
"\n●	Низкий - доходов не хватает на базовые потребности, есть финансовые трудности", reply_markup=get_income_keyboard())
    await state.set_state(SurveyStates.QUESTION_6_INCOME)


@dp.callback_query(F.data.startswith("income_"), SurveyStates.QUESTION_6_INCOME)
async def process_question_6(callback: types.CallbackQuery, state: FSMContext):
    income_map = {
        "income_high": "Высокий",
        "income_above_avg": "Выше среднего",
        "income_avg": "Средний",
        "income_below_avg": "Ниже среднего",
        "income_low": "Низкий"
    }
    answer = income_map[callback.data]
    await callback.message.answer(f"Вы выбрали: {answer}")  # Добавлено
    await save_answer(callback.message.chat.id, 6, answer)
    # Убираем кнопки из сообщения
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("7. Кто регулярно помогает вам с ребенком (из членов семьи и друзей)?")
    await state.set_state(SurveyStates.QUESTION_7_HELP)


@dp.message(SurveyStates.QUESTION_7_HELP)
async def process_question_7(message: types.Message, state: FSMContext):
    help = message.text.strip()
    await save_answer(message.chat.id, 7, help)
    await message.answer("8. Где вы проживаете?", reply_markup=get_location_keyboard())
    await state.set_state(SurveyStates.QUESTION_8_LOCATION)


@dp.callback_query(F.data.startswith("location_"), SurveyStates.QUESTION_8_LOCATION)
async def process_question_8(callback: types.CallbackQuery, state: FSMContext):
    location = "Москва" if callback.data == "location_moscow" else "Московская область"
    await callback.message.answer(f"Вы выбрали: {location}")  # Добавлено
    await callback.message.edit_reply_markup(reply_markup=None)

    if callback.data == "location_mo":
        await callback.message.answer("8а. Укажите населенный пункт:")
        await state.set_state(SurveyStates.QUESTION_8A_LOCATION_DETAIL)
    else:
        await save_answer(callback.message.chat.id, 8, location)
        await callback.message.answer("9. Ходит ли ваш ребенок в детский сад?", reply_markup=get_yes_no_keyboard())
        await state.set_state(SurveyStates.QUESTION_9_KINDERGARTEN)


@dp.message(SurveyStates.QUESTION_8A_LOCATION_DETAIL)
async def process_question_8a(message: types.Message, state: FSMContext):
    location = message.text.strip()
    # Сохраняем полный ответ в одной ячейке
    full_location = f"Московская область, {location}"
    await save_answer(message.chat.id, 8, full_location)
    await message.answer("9. Ходит ли ваш ребенок в детский сад?", reply_markup=get_yes_no_keyboard())
    await state.set_state(SurveyStates.QUESTION_9_KINDERGARTEN)


@dp.callback_query(F.data.in_(["yes", "no"]), SurveyStates.QUESTION_9_KINDERGARTEN)
async def process_question_9(callback: types.CallbackQuery, state: FSMContext):
    answer = "Да" if callback.data == "yes" else "Нет"
    await callback.message.answer(f"Вы выбрали: {answer}")  # Добавлено
    await save_answer(callback.message.chat.id, 9, answer)
    # Убираем кнопки из сообщения
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("10. Пользуетесь ли вы периодически услугами няни?",
                                reply_markup=get_yes_no_keyboard())
    await state.set_state(SurveyStates.QUESTION_10_NANNY)


@dp.callback_query(F.data.in_(["yes", "no"]), SurveyStates.QUESTION_10_NANNY)
async def process_question_10(callback: types.CallbackQuery, state: FSMContext):
    answer = "Да" if callback.data == "yes" else "Нет"
    await callback.message.answer(f"Вы выбрали: {answer}")  # Добавлено
    await save_answer(callback.message.chat.id, 10, answer)
    # Убираем кнопки из сообщения
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("11. Ходит ли ваш ребенок в развивающий центр или кружки?",
                                reply_markup=get_yes_no_keyboard())
    await state.set_state(SurveyStates.QUESTION_11_ACTIVITIES)


@dp.callback_query(F.data.in_(["yes", "no"]), SurveyStates.QUESTION_11_ACTIVITIES)
async def process_question_11(callback: types.CallbackQuery, state: FSMContext):
    answer = "Да" if callback.data == "yes" else "Нет"
    await callback.message.answer(f"Вы выбрали: {answer}")  # Добавлено
    await save_answer(callback.message.chat.id, 11, answer)
    # Убираем кнопки из сообщения
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("12. Есть ли у вас высшее образование?", reply_markup=get_yes_no_keyboard())
    await state.set_state(SurveyStates.QUESTION_12_EDUCATION)


@dp.callback_query(F.data.in_(["yes", "no"]), SurveyStates.QUESTION_12_EDUCATION)
async def process_question_12(callback: types.CallbackQuery, state: FSMContext):
    answer = "Да" if callback.data == "yes" else "Нет"
    await callback.message.answer(f"Вы выбрали: {answer}")  # Добавлено
    await save_answer(callback.message.chat.id, 12, answer)
    # Убираем кнопки из сообщения
    await callback.message.edit_reply_markup(reply_markup=None)

    if callback.data == "yes":
        await callback.message.answer("13. Какое у вас образование?\n\nСфера:")
        await state.set_state(SurveyStates.QUESTION_13_EDUCATION_DETAILS)
    else:
        # Сохраняем "Нет высшего образования" в ячейку для вопроса 13
        await save_answer(callback.message.chat.id, 13, "Нет высшего образования")
        await callback.message.answer("14. Какой у вас график работы?  ?",
                                    reply_markup=get_schedule_keyboard())
        await state.set_state(SurveyStates.QUESTION_14_SCHEDULE)

@dp.message(SurveyStates.QUESTION_13_EDUCATION_DETAILS)
async def process_question_13_field(message: types.Message, state: FSMContext):
    await state.update_data(education_field=message.text.strip())
    await message.answer("Уровень (бакалавр/магистр/специалист):")
    await state.set_state(SurveyStates.QUESTION_13_EDUCATION_LEVEL)


@dp.message(SurveyStates.QUESTION_13_EDUCATION_LEVEL)
async def process_question_13_level(message: types.Message, state: FSMContext):
    await state.update_data(education_level=message.text.strip())
    await message.answer("Год окончания:")
    await state.set_state(SurveyStates.QUESTION_13_EDUCATION_YEAR)


@dp.message(SurveyStates.QUESTION_13_EDUCATION_YEAR)
async def process_question_13_year(message: types.Message, state: FSMContext):
    year = message.text.strip()
    data = await state.get_data()
    education_details = f"Сфера: {data['education_field']}, Уровень: {data['education_level']}, Год: {year}"
    await save_answer(message.chat.id, 13, education_details)
    await message.answer("14. Какой у вас график работы? ", reply_markup=get_schedule_keyboard())
    await state.set_state(SurveyStates.QUESTION_14_SCHEDULE)


@dp.callback_query(F.data.startswith("schedule_"), SurveyStates.QUESTION_14_SCHEDULE)
async def process_question_14(callback: types.CallbackQuery, state: FSMContext):
    schedule_map = {
        "schedule_full_fixed": "Полный рабочий день (фиксированный график)", #Оставить
        "schedule_full_flex": "Полный рабочий день (гибкий график)", #Оставить ответ
        "schedule_part": "Неполный рабочий день",#Оставить ответ
        "schedule_remote": "Удалённо (по графику)",#Убрать ответ
        "schedule_temp": "Временная/проектная работа",#Оставить
        "schedule_no": "Не работаю"#Убрать ответ
    }
    answer = schedule_map[callback.data]
    await callback.message.answer(f"Вы выбрали: {answer}")  # Добавлено
    await save_answer(callback.message.chat.id, 14, answer)
    # Убираем кнопки из сообщения
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("15. В каком формате вы работаете?")
    #На этот вопрос добавить варианты ответов инлайн кнопками
    #В офисе/ на территории работодателя
    #Удалённо (из дома или другого места вне офиса)
    #Гибридный формат (часть времени в офисе, часть удалённо)


    await state.set_state(SurveyStates.QUESTION_15_FIELD)


@dp.message(SurveyStates.QUESTION_15_FIELD)
async def process_question_15(message: types.Message, state: FSMContext):
    field = message.text.strip()
    await save_answer(message.chat.id, 15, field)
    await message.answer("16. В какой сфере вы работаете?", reply_markup=get_yes_no_keyboard()) #тут должен быть открытый вопрос в состоянии FSM без вариантов ответа
    await state.set_state(SurveyStates.QUESTION_16_JOB_CHANGE)


@dp.callback_query(F.data.in_(["yes", "no"]), SurveyStates.QUESTION_16_JOB_CHANGE)
async def process_question_16(callback: types.CallbackQuery, state: FSMContext):
    answer = "Да" if callback.data == "yes" else "Нет"
    await callback.message.answer(f"Вы выбрали: {answer}")
    await save_answer(callback.message.chat.id, 16, answer)
    # Убираем кнопки из сообщения
    await callback.message.edit_reply_markup(reply_markup=None)

    data = await state.get_data()
    success = await save_to_google_sheets(callback.message.chat.id)

    if success:
        await callback.message.answer(
            f"{data['user_name']}, спасибо большое за прохождение анкеты!\n"
            "Ваши ответы успешно сохранены.\n\n"
            "В рамках исследования в течение следующих 2 недель вам необходимо будет заполнить дневник времени за 2 дня:\n\n"
            "1. 1 будний день (понедельник–пятница)\n"
            "2. 1 выходной день (суббота или воскресенье)\n\n"
            "Как это работает:\n\n"
            "1. Мы с вами в переписке договорились, в какие дни недели вам нужно заполнять дневник. Заполнять его можно только в них!\n"
            "2. Вы сами решаете, заполнять дневник на следующей неделе или через неделю\n"
            "3. За день до каждого назначенного дня вы получите напоминание о прохождении",
        )

        await callback.message.answer(
            "Теперь выберите будний день для ведения дневника времени:",
            reply_markup=get_weekdays_keyboard()
        )
    else:
        await callback.message.answer(
            f"{data['user_name']}, спасибо за ответы!\n"
            "К сожалению, произошла ошибка при сохранении данных. "
            "Пожалуйста, сообщите об этом администратору."
        )

    await state.set_state(SurveyStates.SELECT_WEEKDAY)


@dp.callback_query(F.data.startswith("day_"), SurveyStates.SELECT_WEEKDAY)
async def process_weekday_selection(callback: types.CallbackQuery, state: FSMContext):
    day_map = {
        "day_monday": "Понедельник",
        "day_tuesday": "Вторник",
        "day_wednesday": "Среда",
        "day_thursday": "Четверг",
        "day_friday": "Пятница"
    }
    selected_day = day_map.get(callback.data, "Неизвестный день")

    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            "UPDATE participants SET weekday = ? WHERE chat_id = ?",
            (selected_day, callback.message.chat.id)
        )

    await callback.answer(f"Вы выбрали {selected_day} как будний день")
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "Теперь выберите выходной день:",
        reply_markup=get_weekend_keyboard()
    )
    await state.set_state(SurveyStates.SELECT_WEEKEND)


@dp.callback_query(F.data.startswith("day_"), SurveyStates.SELECT_WEEKEND)
async def process_weekend_selection(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_name = data.get('user_name', '')
    day_map = {
        "day_saturday": "Суббота",
        "day_sunday": "Воскресенье"
    }
    selected_day = day_map.get(callback.data, "Неизвестный день")

    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            "UPDATE participants SET weekend = ? WHERE chat_id = ?",
            (selected_day, callback.message.chat.id)
        )

    await callback.answer(f"Вы выбрали {selected_day} как выходной день")
    await callback.message.edit_reply_markup(reply_markup=None)

    # Сохраняем выбранные дни в state для использования в следующих сообщениях
    cursor = conn.cursor()
    cursor.execute(
        "SELECT weekday, weekend FROM participants WHERE chat_id = ?",
        (callback.message.chat.id,)
    )
    days = cursor.fetchone()
    await state.update_data(selected_weekday=days[0], selected_weekend=days[1])

    await callback.message.answer(
        "Перейдем дальше",
        reply_markup=get_understand_keyboard()
    )

    # Отправляем первое сообщение с инструкцией

    await state.set_state(SurveyStates.INSTRUCTION_1)


@dp.callback_query(F.data == "understand", SurveyStates.INSTRUCTION_1)
async def process_instruction_1(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    data = await state.get_data()

    # Получаем текущую дату
    today = datetime.now(pytz.timezone('Europe/Moscow')).date()

    # Словарь для преобразования дней недели
    weekday_map = {
        "Понедельник": 0, "Вторник": 1, "Среда": 2, "Четверг": 3,
        "Пятница": 4, "Суббота": 5, "Воскресенье": 6
    }

    # Рассчитываем даты для буднего дня
    weekday_num = weekday_map[data['selected_weekday']]
    next_weekday = today + timedelta((weekday_num - today.weekday()) % 7)
    if next_weekday <= today:
        next_weekday += timedelta(weeks=1)
    following_weekday = next_weekday + timedelta(weeks=1)

    # Рассчитываем даты для выходного дня
    weekend_num = weekday_map[data['selected_weekend']]
    next_weekend = today + timedelta((weekend_num - today.weekday()) % 7)
    if next_weekend <= today:
        next_weekend += timedelta(weeks=1)
    following_weekend = next_weekend + timedelta(weeks=1)

    # Сохраняем даты в базу данных
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute('''
            UPDATE participants SET 
                weekday_date1 = ?,
                weekday_date2 = ?,
                weekend_date1 = ?,
                weekend_date2 = ?
            WHERE chat_id = ?''',
                     (
                         next_weekday.strftime('%Y-%m-%d'),
                         following_weekday.strftime('%Y-%m-%d'),
                         next_weekend.strftime('%Y-%m-%d'),
                         following_weekend.strftime('%Y-%m-%d'),
                         callback.message.chat.id
                     )
                     )

    await callback.message.answer(
        f"Выбранные для вас дни недели: {data['selected_weekday']} и {data['selected_weekend']}.\n"
        f"Сегодня - {today.strftime('%d.%m.%Y')}, поэтому вы можете заполнить дневник:\n\n"
        f"📅 {data['selected_weekday']}:\n"
        f"- {next_weekday.strftime('%d.%m.%Y')}\n"
        f"- {following_weekday.strftime('%d.%m.%Y')}\n\n"
        f"📅 {data['selected_weekend']}:\n"
        f"- {next_weekend.strftime('%d.%m.%Y')}\n"
        f"- {following_weekend.strftime('%d.%m.%Y')}",
        reply_markup=get_understand_keyboard()
    )
    await state.set_state(SurveyStates.INSTRUCTION_2)


@dp.callback_query(F.data == "understand", SurveyStates.INSTRUCTION_2)
async def process_instruction_2(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "В ходе дневника вам нужно будет последовательно описать, как проходит ваш день, с разбивкой по 20-минутным промежуткам. "
        "Настоятельно прошу вас заполнять дневник несколько раз за день (например, два раза: в обед и вечером перед сном), "
        "чтобы ничего не упустить.",
        reply_markup=get_understand_keyboard()
    )
    await state.set_state(SurveyStates.INSTRUCTION_3)


@dp.callback_query(F.data == "understand", SurveyStates.INSTRUCTION_3)
async def process_instruction_3(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "Как работает заполнение?\n\n"
        "Начало дня: Вы указываете время пробуждения в 24-часовом формате через двоеточие (например, 07:30 или 09:23). "
        "Затем, система автоматически определит первый 20-минутный промежуток (например, 07:20–07:40 или 07:40–08:00), "
        "который вам нужно будет описать.\n\n"
        "Для каждого промежутка вам зададут 3 вопроса:\n\n"
        "1) Чем вы занимались? (Примеры ответа: 'Я помыла посуду, затем готовила ужин. Параллельно разговаривала с подругой по телефону'. "
        "'Я была на совещании, в середине мне позвонили из детского сада, я ответила, потом вернулась на совещание'). "
        "Пожалуйста, отвечайте на этот вопрос настолько полно насколько возможно. Укажите все действия, которые вы делали, "
        "включая те, которые выполнялись одновременно.\n\n"
        "2) Где вы были? (Можно выбрать несколько вариантов: дома, на работе и т.д.).\n\n"
        "3) С кем вы были? (Можно выбрать несколько вариантов: ребенок, муж, одна и др.).\n\n"
        "Автоматический переход: После заполнения одного промежутка бот сразу предложит следующий (например, 08:00–08:20).\n\n"
        "Окончание заполнения: Как только ваш день закончится, напишите 'Ночной сон' в ответ на вопрос 'Чем вы занимались' - дневник закроется.",
        reply_markup=get_understand_keyboard()
    )
    await state.set_state(SurveyStates.INSTRUCTION_4)


@dp.callback_query(F.data == "understand", SurveyStates.INSTRUCTION_4)
async def process_instruction_4(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    data = await state.get_data()
    await callback.message.answer(
        f"Если у вас после прочтения инструкции возникли вопросы, пожалуйста, напишите мне в Telegram: @moi_e_va или в WhatsApp: 89629574866.\n\n"
        f"Еще раз благодарю вас, {data['user_name']}, за участие в исследовании. Удачи в заполнении дневников!"
    )
    await state.set_state(SurveyStates.FINISHED)



@dp.message(
    night_sleep_filter,
    StateFilter(
        DiaryStates.WAITING_FOR_WAKE_UP,
        DiaryStates.RECORDING_ACTIVITY,
        DiaryStates.RECORDING_LOCATION,
        DiaryStates.RECORDING_COMPANIONS
    )
)
async def handle_night_sleep_anywhere(message: types.Message, state: FSMContext):
    await finish_diary(message, state)


@dp.message(DiaryStates.FEEDBACK_QUESTION_1)
async def process_feedback_1(message: types.Message, state: FSMContext):
    data = await state.get_data()
    worksheet = data['worksheet']
    username_to_find = data['username_to_find']

    # Обработка голосового сообщения
    if message.voice:
        # Формируем подпись
        caption = (f"Ответ на вопрос 1 от @{message.from_user.username or 'нет username'}\n"
                   f"Время: {datetime.now(pytz.timezone('Europe/Moscow')).strftime('%Y-%m-%d %H:%M')}")

        # Пересылаем в группу
        await bot.send_voice(
            chat_id=GROUP_ID,
            voice=message.voice.file_id,
            caption=caption
        )

        # Сохраняем в таблицу отметку о голосовом ответе
        try:
            cell = worksheet.find(username_to_find)
            last_col = len(worksheet.row_values(cell.row))
            worksheet.update_cell(cell.row, last_col + 1, "Ответ на вопрос 1: [голосовое сообщение]")
        except Exception as e:
            print(f"Ошибка при сохранении ответа: {e}")
    else:
        # Обычная обработка текстового ответа
        try:
            cell = worksheet.find(username_to_find)
            last_col = len(worksheet.row_values(cell.row))
            worksheet.update_cell(cell.row, last_col + 1, "Ответ на вопрос 1: " + message.text)
        except Exception as e:
            print(f"Ошибка при сохранении ответа: {e}")

    await message.answer(
        "Спасибо большое за ответ! Опишите, пожалуйста, как изменилось ваше представление "
        "о том, как вы используете время, после ведения дневника?"
    )
    await state.set_state(DiaryStates.FEEDBACK_QUESTION_2)


@dp.message(DiaryStates.FEEDBACK_QUESTION_2)
async def process_feedback_2(message: types.Message, state: FSMContext):
    data = await state.get_data()
    worksheet = data['worksheet']
    username_to_find = data['username_to_find']

    # Обработка голосового сообщения
    if message.voice:
        # Формируем подпись
        caption = (f"Ответ на вопрос 2 от @{message.from_user.username or 'нет username'}\n"
                   f"Время: {datetime.now(pytz.timezone('Europe/Moscow')).strftime('%Y-%m-%d %H:%M')}")

        # Пересылаем в группу
        await bot.send_voice(
            chat_id=GROUP_ID,
            voice=message.voice.file_id,
            caption=caption
        )

        # Сохраняем в таблицу отметку о голосовом ответе
        try:
            cell = worksheet.find(username_to_find)
            last_col = len(worksheet.row_values(cell.row))
            worksheet.update_cell(cell.row, last_col + 1, "Ответ на вопрос 2: [голосовое сообщение]")
        except Exception as e:
            print(f"Ошибка при сохранении ответа: {e}")
    else:
        # Обычная обработка текстового ответа
        try:
            cell = worksheet.find(username_to_find)
            last_col = len(worksheet.row_values(cell.row))
            worksheet.update_cell(cell.row, last_col + 1, "Ответ на вопрос 2: " + message.text)
        except Exception as e:
            print(f"Ошибка при сохранении ответа: {e}")

    await message.answer(
        "И финально, поделитесь, пожалуйста, вашими впечатлениями от ведения дневника: "
        "что оказалось удобным, а что вызвало сложности? Было ли для вас это занятие трудным? "
        "Может быть, вы сделали какие-то интересные наблюдения о себе в процессе?"
    )
    await state.set_state(DiaryStates.FEEDBACK_QUESTION_3)


@dp.message(DiaryStates.FEEDBACK_QUESTION_3)
async def process_feedback_3(message: types.Message, state: FSMContext):
    data = await state.get_data()
    worksheet = data['worksheet']
    username_to_find = data['username_to_find']

    # Обработка голосового сообщения
    if message.voice:
        # Формируем подпись
        caption = (f"Ответ на вопрос 3 от @{message.from_user.username or 'нет username'}\n"
                   f"Время: {datetime.now(pytz.timezone('Europe/Moscow')).strftime('%Y-%m-%d %H:%M')}")

        # Пересылаем в группу
        await bot.send_voice(
            chat_id=GROUP_ID,
            voice=message.voice.file_id,
            caption=caption
        )

        # Сохраняем в таблицу отметку о голосовом ответе
        try:
            cell = worksheet.find(username_to_find)
            last_col = len(worksheet.row_values(cell.row))
            worksheet.update_cell(cell.row, last_col + 1, "Ответ на вопрос 3: [голосовое сообщение]")
        except Exception as e:
            print(f"Ошибка при сохранении ответа: {e}")
    else:
        # Обычная обработка текстового ответа
        try:
            cell = worksheet.find(username_to_find)
            last_col = len(worksheet.row_values(cell.row))
            worksheet.update_cell(cell.row, last_col + 1, "Ответ на вопрос 3: " + message.text)
        except Exception as e:
            print(f"Ошибка при сохранении ответа: {e}")

    # Очищаем записи дневника для этого пользователя
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute('DELETE FROM diary_entries WHERE chat_id = ?', (message.chat.id,))

    await message.answer(
        "Огромное спасибо за ваше время, внимание и искренность при заполнении дневника! "
        "Каждая ваша запись – это ценный вклад в мое исследование. Я знаю, что вести дневник – "
        "это непростая задача, требующая дисциплины и внимания к деталям. Вы прекрасно справились! "
        "Увидимся с вами на интервью✨"
    )
    await state.clear()



@dp.startup()
async def on_startup():
    create_tables()


async def main():
    print("Бот исследования запущен")
    # Создаем фоновую задачу
    asyncio.create_task(background_task())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())