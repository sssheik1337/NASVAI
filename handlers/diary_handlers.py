import logging
from aiogram import Dispatcher, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, StateFilter
from states import DiaryStates, SurveyStates
from keyboards import get_childcare_buttons, get_same_location_buttons, get_same_companions_buttons
from datetime import datetime, timedelta
import sqlite3
import pytz
from config import GROUP_ID

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
            diary_start_time=now.strftime("%Y-%m-%d %H:%M:%S"),
            previous_location=None,
            previous_companions=[],
            previous_childcare=None,
            entry_count=0
        )
        await ask_activity_question(message, state)
    except ValueError:
        await message.answer("Пожалуйста, введите время в формате ЧЧ:MM (например, 07:30)")

async def ask_activity_question(message: types.Message, state: FSMContext):
    data = await state.get_data()
    entry_count = data.get('entry_count', 0) + 1
    await state.update_data(entry_count=entry_count)
    await message.answer(
        f"📝 Период времени: {data['current_period_start']}-{data['current_period_end']}\n\n"
        f"1. Чем вы занимались с {data['current_period_start']} до {data['current_period_end']}? "
        "(Опишите все ваши действия, включая параллельные и короткие занятия)"
    )
    await state.set_state(DiaryStates.RECORDING_ACTIVITY)

async def process_activity(message: types.Message, state: FSMContext):
    user_answer = message.text.strip()
    if user_answer.lower() == "ночной сон":
        await finish_diary(message, state)
        return
    await state.update_data(current_activity=user_answer)
    data = await state.get_data()
    if data.get('entry_count', 0) == 1:
        await message.answer("2. Где вы были в это время?")
        await state.set_state(DiaryStates.RECORDING_LOCATION)
    else:
        await message.answer("2. Где вы были в это время?", reply_markup=get_same_location_buttons())
        await state.set_state(DiaryStates.RECORDING_LOCATION)

async def process_location(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if callback.data == "loc_same":
        await callback.message.answer("Вы выбрали вариант: Я была там же")
        await state.update_data(current_location=data.get('previous_location', ''))
        await callback.message.answer("3. С кем вы были в это время?", reply_markup=get_same_companions_buttons())
        await state.set_state(DiaryStates.RECORDING_COMPANIONS)
    elif callback.data == "loc_different":
        await callback.message.answer("Напишите, пожалуйста, где вы были:")
        await state.set_state(DiaryStates.RECORDING_LOCATION_OTHER)
    await callback.message.edit_reply_markup(reply_markup=None)

async def process_location_text(message: types.Message, state: FSMContext):
    location = message.text.strip()
    await state.update_data(current_location=location, previous_location=location)
    data = await state.get_data()
    if data.get('entry_count', 0) == 1:
        await message.answer("3. С кем вы были в это время?")
        await state.set_state(DiaryStates.RECORDING_COMPANIONS)
    else:
        await message.answer("3. С кем вы были в это время?", reply_markup=get_same_companions_buttons())
        await state.set_state(DiaryStates.RECORDING_COMPANIONS)

async def process_location_other(message: types.Message, state: FSMContext):
    location = message.text.strip()
    await state.update_data(current_location=location, previous_location=location)
    await message.answer("3. С кем вы были в это время?", reply_markup=get_same_companions_buttons())
    await state.set_state(DiaryStates.RECORDING_COMPANIONS)

async def process_companions(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if callback.data == "comp_same":
        await callback.message.answer("Вы выбрали вариант: Я была с теми же людьми")
        await state.update_data(current_companions=data.get('previous_companions', []))
        if data.get('entry_count', 0) == 1:
            await callback.message.answer("4. Кто присматривал за вашим ребенком в это время?")
        else:
            await callback.message.answer("4. Кто присматривал за вашим ребенком в это время?", reply_markup=get_childcare_buttons())
        await state.set_state(DiaryStates.RECORDING_CHILDCARE)
    elif callback.data == "comp_different":
        await callback.message.answer("Напишите, пожалуйста, с кем вы были:")
        await state.set_state(DiaryStates.RECORDING_COMPANIONS_OTHER)
    await callback.message.edit_reply_markup(reply_markup=None)

async def process_companions_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    current_companions = data.get('current_companions', [])
    current_companions.append(message.text.strip())
    await state.update_data(current_companions=current_companions, previous_companions=current_companions)
    if data.get('entry_count', 0) == 1:
        await message.answer("4. Кто присматривал за вашим ребенком в это время?")
    else:
        await message.answer("4. Кто присматривал за вашим ребенком в это время?", reply_markup=get_childcare_buttons())
    await state.set_state(DiaryStates.RECORDING_CHILDCARE)

async def process_companions_other(message: types.Message, state: FSMContext):
    data = await state.get_data()
    current_companions = data.get('current_companions', [])
    current_companions.append(message.text.strip())
    await state.update_data(current_companions=current_companions, previous_companions=current_companions)
    if data.get('entry_count', 0) == 1:
        await message.answer("4. Кто присматривал за вашим ребенком в это время?")
    else:
        await message.answer("4. Кто присматривал за вашим ребенком в это время?", reply_markup=get_childcare_buttons())
    await state.set_state(DiaryStates.RECORDING_CHILDCARE)

async def process_childcare(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if callback.data == "childcare_same":
        await callback.message.answer("Вы выбрали вариант: Ситуация не менялась")
        await state.update_data(current_childcare=data.get('previous_childcare', ''))
        await save_diary_entry(callback.message, state)
    elif callback.data == "childcare_different":
        await callback.message.answer("Напишите, пожалуйста, кто присматривал за вашим ребенком:")
        await state.set_state(DiaryStates.RECORDING_CHILDCARE_OTHER)
    await callback.message.edit_reply_markup(reply_markup=None)

async def process_childcare_text(message: types.Message, state: FSMContext):
    childcare = message.text.strip()
    await state.update_data(current_childcare=childcare, previous_childcare=childcare)
    await save_diary_entry(message, state)

async def process_childcare_other(message: types.Message, state: FSMContext):
    childcare = message.text.strip()
    await state.update_data(current_childcare=childcare, previous_childcare=childcare)
    await save_diary_entry(message, state)

async def save_diary_entry(message: types.Message, state: FSMContext):
    data = await state.get_data()
    current_companions = data.get('current_companions', [])
    companions_str = ", ".join(current_companions)
    now = datetime.now(pytz.timezone('Europe/Moscow'))
    now_full = now.strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect("research_bot.db") as conn:
        conn.execute('''
            INSERT INTO diary_entries 
            (chat_id, username, entry_date, timestamp, time_period, activity, location, companions, childcare)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                     (
                         message.chat.id,
                         message.from_user.username,
                         now.strftime('%Y-%m-%d'),
                         now_full,
                         f"{data['current_period_start']}-{data['current_period_end']}",
                         data.get('current_activity', ''),
                         data.get('current_location', ''),
                         companions_str,
                         data.get('current_childcare', '')
                     ))
    current_end = datetime.strptime(data['current_period_end'], "%H:%M").time()
    next_start = current_end
    next_end = (datetime.combine(now.date(), next_start) + timedelta(minutes=20)).time()
    await state.update_data(
        current_period_start=next_start.strftime("%H:%M"),
        current_period_end=next_end.strftime("%H:%M"),
        current_companions=[]
    )
    await ask_activity_question(message, state)

async def finish_diary(message: types.Message, state: FSMContext):
    with sqlite3.connect("research_bot.db") as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT time_period, activity, location, companions, childcare, timestamp, username 
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
        time_period, activity, location, companions, childcare, timestamp, username = entry
        report_line = (
            f"В промежуток [{time_period}] пользователь [{username or 'нет username'} - {user_name}] "
            f"делал [{activity}] в локации [{location}] с компанией [{companions}] "
            f"присмотр за ребенком: [{childcare}]. Запись оставил в [{timestamp}]."
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
        if username_to_find:
            try:
                cell = worksheet.find(username_to_find)
                diary_column = 22 if new_count == 1 else 23  # Столбец V (22) для дневника 1, W (23) для дневника 2
                worksheet.update_cell(cell.row, diary_column, full_report)
                logger.info(f"Отчет дневника {new_count} успешно добавлен в строку {cell.row}, столбец {diary_column}")
                if new_count == 2:
                    await state.set_data({'worksheet': worksheet, 'username_to_find': username_to_find})
                    await message.answer(
                        "Далее, я попрошу вас ответить на несколько вопросов об опыте заполнения дневника. "
                        "Вы можете отвечать в свободной форме (написать текстом или записать голосовое сообщение).\n\n"
                        "Первый вопрос: отражает ли ваш дневник привычный для вас распорядок, или эти дни "
                        "чем-то выделялись из вашей обычной рутины? Расскажите, пожалуйста, поподробней."
                    )
                    await state.set_state(DiaryStates.FEEDBACK_QUESTION_1)
                    return
            except Exception as e:
                logger.error(f"Ошибка при сохранении отчета дневника {new_count} в Google Sheets: {e}")
        else:
            logger.error("Username не найден, невозможно добавить отчет")
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
    dp.callback_query.register(process_location, F.data.in_(["loc_same", "loc_different"]), DiaryStates.RECORDING_LOCATION)
    dp.message.register(process_location_text, DiaryStates.RECORDING_LOCATION)
    dp.message.register(process_location_other, DiaryStates.RECORDING_LOCATION_OTHER)
    dp.callback_query.register(process_companions, F.data.in_(["comp_same", "comp_different"]), DiaryStates.RECORDING_COMPANIONS)
    dp.message.register(process_companions_text, DiaryStates.RECORDING_COMPANIONS)
    dp.message.register(process_companions_other, DiaryStates.RECORDING_COMPANIONS_OTHER)
    dp.callback_query.register(process_childcare, F.data.in_(["childcare_same", "childcare_different"]), DiaryStates.RECORDING_CHILDCARE)
    dp.message.register(process_childcare_text, DiaryStates.RECORDING_CHILDCARE)
    dp.message.register(process_childcare_other, DiaryStates.RECORDING_CHILDCARE_OTHER)
    dp.message.register(finish_diary, F.text.lower() == "ночной сон", StateFilter(
        DiaryStates.WAITING_FOR_WAKE_UP,
        DiaryStates.RECORDING_ACTIVITY,
        DiaryStates.RECORDING_LOCATION,
        DiaryStates.RECORDING_COMPANIONS,
        DiaryStates.RECORDING_CHILDCARE,
        DiaryStates.RECORDING_CHILDCARE_OTHER
    ))