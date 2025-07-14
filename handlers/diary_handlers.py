from aiogram import Dispatcher, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, StateFilter
from states import DiaryStates, SurveyStates
from keyboards import get_location_buttons, get_companions_buttons, get_yes_no_keyboard
from datetime import datetime, timedelta
import sqlite3
import pytz
from config import GROUP_ID
import logging

logger = logging.getLogger(__name__)

async def cmd_start_diary(message: types.Message, state: FSMContext):
    await message.answer(
        "Начинаем ведение дневника времени. Пожалуйста, укажите время вашего пробуждения "
        "в 24-часовом формате (например, 07:30 или 09:45):"
    )
    await state.set_state(DiaryStates.WAITING_FOR_WAKE_UP)

async def process_wake_up_time(message: types.Message, state: FSMContext):
    try:
        wake_up_time = datetime.strptime(message.text.strip(), "%H:%M").time()
        now = datetime.now(pytz.timezone('Europe/Moscow'))
        start_minute = (wake_up_time.minute // 20) * 20
        current_period_start = wake_up_time.replace(minute=start_minute, second=0)
        current_period_end = (datetime.combine(now.date(), current_period_start) + timedelta(minutes=20)).time()
        await state.update_data(
            diary_entries=[],
            current_period_start=current_period_start.strftime("%H:%M"),
            current_period_end=current_period_end.strftime("%H:%M"),
            wake_up_time=wake_up_time.strftime("%H:%M"),
            diary_start_time=now.strftime("%Y-%m-%d %H:%M:%S")
        )
        await ask_activity_question(message, state)
    except ValueError:
        await message.answer("Пожалуйста, введите время в формате ЧЧ:MM (например, 07:30)")

async def ask_activity_question(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await message.answer(
        f"📝 Период времени: {data['current_period_start']}-{data['current_period_end']}\n\n"
        "1. Чем вы занимались в это время? (Опишите все ваши действия, включая параллельные)"
    )
    await state.set_state(DiaryStates.RECORDING_ACTIVITY)

async def process_activity(message: types.Message, state: FSMContext):
    user_answer = message.text.strip()
    if user_answer.lower() == "ночной сон":
        await finish_diary(message, state)
        return
    await state.update_data(current_activity=user_answer)
    await message.answer("2. Где вы находились в это время?", reply_markup=get_location_buttons())
    await state.set_state(DiaryStates.RECORDING_LOCATION)

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
        await callback.message.answer("3. С кем вы были в это время?", reply_markup=get_companions_buttons())
        await state.set_state(DiaryStates.RECORDING_COMPANIONS)
    await callback.message.edit_reply_markup(reply_markup=None)

async def process_location_other(message: types.Message, state: FSMContext):
    await state.update_data(current_location=f"Другое: {message.text.strip()}")
    await message.answer("3. С кем вы были в это время?", reply_markup=get_companions_buttons())
    await state.set_state(DiaryStates.RECORDING_COMPANIONS)

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
        await callback.message.answer(
            f"Вы выбрали: {', '.join(current_companions)}\nХотите добавить еще кого-то?",
            reply_markup=get_yes_no_keyboard()
        )
        await state.set_state(DiaryStates.ASKING_ADD_COMPANION)
    await callback.message.edit_reply_markup(reply_markup=None)

async def process_companions_other(message: types.Message, state: FSMContext):
    data = await state.get_data()
    current_companions = data.get('current_companions', [])
    current_companions.append(f"Другие: {message.text.strip()}")
    await state.update_data(current_companions=current_companions)
    await message.answer(
        f"Вы выбрали: {', '.join(current_companions)}\nХотите добавить еще кого-то?",
        reply_markup=get_yes_no_keyboard()
    )
    await state.set_state(DiaryStates.ASKING_ADD_COMPANION)

async def process_add_companion(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "yes":
        await callback.message.answer("Кого еще добавить?", reply_markup=get_companions_buttons())
        await state.set_state(DiaryStates.RECORDING_COMPANIONS)
    else:
        data = await state.get_data()
        current_companions = data.get('current_companions', [])
        companions_str = ", ".join(current_companions)
        now = datetime.now(pytz.timezone('Europe/Moscow'))
        now_full = now.strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect("research_bot.db") as conn:
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
                         ))
        current_end = datetime.strptime(data['current_period_end'], "%H:%M").time()
        next_start = current_end
        next_end = (datetime.combine(now.date(), next_start) + timedelta(minutes=20)).time()
        await state.update_data(
            current_period_start=next_start.strftime("%H:%M"),
            current_period_end=next_end.strftime("%H:%M"),
            current_companions=[]
        )
        await ask_activity_question(callback.message, state)
    await callback.message.edit_reply_markup(reply_markup=None)

async def finish_diary(message: types.Message, state: FSMContext):
    with sqlite3.connect("research_bot.db") as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT time_period, activity, location, companions, timestamp, username 
            FROM diary_entries 
            WHERE chat_id = ? 
            ORDER BY timestamp''',
                       (message.chat.id,))
        entries = cursor.fetchall()
        cursor.execute('SELECT name, count FROM participants WHERE chat_id = ?', (message.chat.id,))
        user_data = cursor.fetchone()
        user_name = user_data[0] if user_data else "Неизвестный пользователь"
        current_count = user_data[1] if user_data else 0
        new_count = current_count + 1
        cursor.execute('UPDATE participants SET count = ? WHERE chat_id = ?', (new_count, message.chat.id))
        conn.commit()
    report = []
    for entry in entries:
        time_period, activity, location, companions, timestamp, username = entry
        report_line = (
            f"В промежуток [{time_period}] пользователь [{username or 'нет username'} - {user_name}] "
            f"делал [{activity}] в локации [{location}] с компанией [{companions}]. "
            f"Запись оставил в [{timestamp}]."
        )
        report.append(report_line)
    full_report = "\n".join(report)
    logger.info("\n" + "=" * 50)
    logger.info("ОТЧЕТ О ДЕЯТЕЛЬНОСТИ ПОЛЬЗОВАТЕЛЯ:")
    logger.info(full_report)
    logger.info("=" * 50 + "\n")
    try:
        from google_sheets import init_google_sheets
        worksheet = init_google_sheets()
        username_to_find = f"@{message.from_user.username}" if message.from_user.username else None
        if new_count == 2:
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
                    last_col = len(worksheet.row_values(cell.row))
                    worksheet.update_cell(cell.row, last_col + 1, full_report)
                    print(f"Отчет успешно добавлен в строку {cell.row}")
                except Exception as e:
                    logger.error(f"Ошибка при сохранении в Google Sheets: {e}")
            else:
                print("Username не найден, невозможно добавить отчет")
    except Exception as e:
        logger.error(f"Ошибка при сохранении в Google Sheets: {e}")
    with sqlite3.connect("research_bot.db") as conn:
        conn.execute('DELETE FROM diary_entries WHERE chat_id = ?', (message.chat.id,))
    await message.answer(
        "Дневник времени успешно сохранен! Спасибо за ваши записи.\n"
        "Вы можете продолжить в другой раз, снова используя команду /start_diary."
    )
    await state.clear()

def register_handlers(dp: Dispatcher, bot: Bot):
    dp.message.register(cmd_start_diary, Command("start_diary"))
    dp.message.register(process_wake_up_time, DiaryStates.WAITING_FOR_WAKE_UP)
    dp.message.register(process_activity, DiaryStates.RECORDING_ACTIVITY)
    dp.callback_query.register(process_location, F.data.startswith("loc_"), DiaryStates.RECORDING_LOCATION)
    dp.message.register(process_location_other, DiaryStates.RECORDING_LOCATION_OTHER)
    dp.callback_query.register(process_companions, F.data.startswith("comp_"), DiaryStates.RECORDING_COMPANIONS)
    dp.message.register(process_companions_other, DiaryStates.RECORDING_COMPANIONS_OTHER)
    dp.callback_query.register(process_add_companion, F.data.in_(["yes", "no"]), DiaryStates.ASKING_ADD_COMPANION)
    dp.message.register(finish_diary, F.text.lower() == "ночной сон", StateFilter(
        DiaryStates.WAITING_FOR_WAKE_UP,
        DiaryStates.RECORDING_ACTIVITY,
        DiaryStates.RECORDING_LOCATION,
        DiaryStates.RECORDING_COMPANIONS
    ))