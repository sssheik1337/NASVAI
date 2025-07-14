from aiogram import Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from states import SurveyStates
from keyboards import get_start_keyboard, get_yes_no_keyboard, get_income_keyboard, get_location_keyboard, get_schedule_keyboard, get_weekdays_keyboard, get_weekend_keyboard, get_understand_keyboard
from database import save_answer
from google_sheets import save_to_google_sheets
from datetime import datetime, timedelta
import sqlite3
import pytz
import logging

logger = logging.getLogger(__name__)

async def cmd_start(message: types.Message, state: FSMContext):
    welcome_text = """
Здравствуйте✨

Большое спасибо вам за участие в моем исследовании, посвященном возвращению женщин после декретного отпуска на работу. Все данные, которые вы здесь предоставите, будут полностью анонимными, а в итоговой исследовательской работе будут указаны в обобщенном виде.

Спасибо за ваш вклад в развитие социальных исследований! Ваши ответы помогут создать более эффективные программы поддержки для женщин в аналогичной ситуации.

Для старта отправьте "Начать".
    """
    await message.answer(welcome_text, reply_markup=get_start_keyboard())
    await state.set_state(SurveyStates.WAITING_FOR_START)

async def handle_start_survey(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("Подскажите, пожалуйста, как я могу к вам обращаться?")
    await state.set_state(SurveyStates.ASKING_NAME)

async def process_user_name(message: types.Message, state: FSMContext):
    user_name = message.text.strip()
    await state.update_data(user_name=user_name)
    try:
        with sqlite3.connect("research_bot.db") as conn:
            conn.execute(
                '''INSERT OR REPLACE INTO participants 
                (chat_id, name, username) 
                VALUES (?, ?, ?)''',
                (message.chat.id, user_name, message.from_user.username)
            )
    except Exception as e:
        logger.error(f"Ошибка сохранения данных: {e}")
        await message.answer("Произошла ошибка при сохранении данных. Пожалуйста, попробуйте позже.")
        return
    await message.answer(
        f"{user_name}, в качестве первого этапа, предлагаю вам пройти короткую анкету. "
        f"Она состоит из 16 вопросов о вашей семье, образовании, занятости и поддержке в уходе за ребенком. "
        f"Заполнение займет около 5 минут. Это поможет мне узнать о вас чуть-чуть побольше, а также облегчит дальнейшие интервью."
        f"\n\n1. Сколько вам лет?"
    )
    await state.set_state(SurveyStates.QUESTION_1_AGE)

async def process_question_1(message: types.Message, state: FSMContext):
    age = message.text.strip()
    await save_answer(message.chat.id, 1, age)
    await message.answer("2. Есть ли у вас муж?", reply_markup=get_yes_no_keyboard())
    await state.set_state(SurveyStates.QUESTION_2_HUSBAND)

async def process_question_2(callback: types.CallbackQuery, state: FSMContext):
    answer = "Да" if callback.data == "yes" else "Нет"
    await callback.message.answer(f"Вы выбрали: {answer}")
    await save_answer(callback.message.chat.id, 2, answer)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("3. Сколько у вас детей?")
    await state.set_state(SurveyStates.QUESTION_3_CHILDREN_COUNT)

async def process_question_3(message: types.Message, state: FSMContext):
    count = message.text.strip()
    await save_answer(message.chat.id, 3, count)
    await message.answer("4. Сколько лет вашему ребенку?")
    await state.set_state(SurveyStates.QUESTION_4_CHILD_AGE)

async def process_question_4(message: types.Message, state: FSMContext):
    age = message.text.strip()
    await save_answer(message.chat.id, 4, age)
    await message.answer("5. Опишите состав вашей семьи (тех, кто живет с вами в одном доме).")
    await state.set_state(SurveyStates.QUESTION_5_FAMILY)

async def process_question_5(message: types.Message, state: FSMContext):
    family = message.text.strip()
    await save_answer(message.chat.id, 5, family)
    await message.answer(
        "6. Как вы оцениваете доход своей семьи?\n"
        "● Высокий - свободно покрываем все расходы, включая путешествия и крупные покупки, откладываем сбережения\n"
        "● Выше среднего - хватает на комфортную жизнь и развлечения, но дорогие покупки требуют накоплений\n"
        "● Средний - средств достаточно на основные нужды (еда, жилье, одежда), но на дополнительные траты остаётся мало\n"
        "● Ниже среднего - денег хватает только на самое необходимое, приходится строго экономить\n"
        "● Низкий - доходов не хватает на базовые потребности, есть финансовые трудности",
        reply_markup=get_income_keyboard()
    )
    await state.set_state(SurveyStates.QUESTION_6_INCOME)

async def process_question_6(callback: types.CallbackQuery, state: FSMContext):
    income_map = {
        "income_high": "Высокий",
        "income_above_avg": "Выше среднего",
        "income_avg": "Средний",
        "income_below_avg": "Ниже среднего",
        "income_low": "Низкий"
    }
    answer = income_map[callback.data]
    await callback.message.answer(f"Вы выбрали: {answer}")
    await save_answer(callback.message.chat.id, 6, answer)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("7. Кто регулярно помогает вам с ребенком (из членов семьи и друзей)?")
    await state.set_state(SurveyStates.QUESTION_7_HELP)

async def process_question_7(message: types.Message, state: FSMContext):
    help = message.text.strip()
    await save_answer(message.chat.id, 7, help)
    await message.answer("8. Где вы проживаете?", reply_markup=get_location_keyboard())
    await state.set_state(SurveyStates.QUESTION_8_LOCATION)

async def process_question_8(callback: types.CallbackQuery, state: FSMContext):
    location = "Москва" if callback.data == "location_moscow" else "Московская область"
    await callback.message.answer(f"Вы выбрали: {location}")
    await callback.message.edit_reply_markup(reply_markup=None)
    if callback.data == "location_mo":
        await callback.message.answer("8а. Укажите населенный пункт:")
        await state.set_state(SurveyStates.QUESTION_8A_LOCATION_DETAIL)
    else:
        await save_answer(callback.message.chat.id, 8, location)
        await callback.message.answer("9. Ходит ли ваш ребенок в детский сад?", reply_markup=get_yes_no_keyboard())
        await state.set_state(SurveyStates.QUESTION_9_KINDERGARTEN)

async def process_question_8a(message: types.Message, state: FSMContext):
    location = message.text.strip()
    full_location = f"Московская область, {location}"
    await save_answer(message.chat.id, 8, full_location)
    await message.answer("9. Ходит ли ваш ребенок в детский сад?", reply_markup=get_yes_no_keyboard())
    await state.set_state(SurveyStates.QUESTION_9_KINDERGARTEN)

async def process_question_9(callback: types.CallbackQuery, state: FSMContext):
    answer = "Да" if callback.data == "yes" else "Нет"
    await callback.message.answer(f"Вы выбрали: {answer}")
    await save_answer(callback.message.chat.id, 9, answer)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("10. Пользуетесь ли вы периодически услугами няни?", reply_markup=get_yes_no_keyboard())
    await state.set_state(SurveyStates.QUESTION_10_NANNY)

async def process_question_10(callback: types.CallbackQuery, state: FSMContext):
    answer = "Да" if callback.data == "yes" else "Нет"
    await callback.message.answer(f"Вы выбрали: {answer}")
    await save_answer(callback.message.chat.id, 10, answer)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("11. Ходит ли ваш ребенок в развивающий центр или кружки?", reply_markup=get_yes_no_keyboard())
    await state.set_state(SurveyStates.QUESTION_11_ACTIVITIES)

async def process_question_11(callback: types.CallbackQuery, state: FSMContext):
    answer = "Да" if callback.data == "yes" else "Нет"
    await callback.message.answer(f"Вы выбрали: {answer}")
    await save_answer(callback.message.chat.id, 11, answer)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("12. Есть ли у вас высшее образование?", reply_markup=get_yes_no_keyboard())
    await state.set_state(SurveyStates.QUESTION_12_EDUCATION)

async def process_question_12(callback: types.CallbackQuery, state: FSMContext):
    answer = "Да" if callback.data == "yes" else "Нет"
    await callback.message.answer(f"Вы выбрали: {answer}")
    await save_answer(callback.message.chat.id, 12, answer)
    await callback.message.edit_reply_markup(reply_markup=None)
    if callback.data == "yes":
        await callback.message.answer("13. Какое у вас образование?\n\nСфера:")
        await state.set_state(SurveyStates.QUESTION_13_EDUCATION_DETAILS)
    else:
        await save_answer(callback.message.chat.id, 13, "Нет высшего образования")
        await callback.message.answer("14. Какой у вас график работы?", reply_markup=get_schedule_keyboard())
        await state.set_state(SurveyStates.QUESTION_14_SCHEDULE)

async def process_question_13_field(message: types.Message, state: FSMContext):
    await state.update_data(education_field=message.text.strip())
    await message.answer("Уровень (бакалавр/магистр/специалист):")
    await state.set_state(SurveyStates.QUESTION_13_EDUCATION_LEVEL)

async def process_question_13_level(message: types.Message, state: FSMContext):
    await state.update_data(education_level=message.text.strip())
    await message.answer("Год окончания:")
    await state.set_state(SurveyStates.QUESTION_13_EDUCATION_YEAR)

async def process_question_13_year(message: types.Message, state: FSMContext):
    year = message.text.strip()
    data = await state.get_data()
    education_details = f"Сфера: {data['education_field']}, Уровень: {data['education_level']}, Год: {year}"
    await save_answer(message.chat.id, 13, education_details)
    await message.answer("14. Какой у вас график работы?", reply_markup=get_schedule_keyboard())
    await state.set_state(SurveyStates.QUESTION_14_SCHEDULE)

async def process_question_14(callback: types.CallbackQuery, state: FSMContext):
    schedule_map = {
        "schedule_full_fixed": "Полный рабочий день (фиксированный график)",
        "schedule_full_flex": "Полный рабочий день (гибкий график)",
        "schedule_part": "Неполный рабочий день",
        "schedule_remote": "Удалённо (по графику)",
        "schedule_temp": "Временная/проектная работа",
        "schedule_no": "Не работаю"
    }
    answer = schedule_map[callback.data]
    await callback.message.answer(f"Вы выбрали: {answer}")
    await save_answer(callback.message.chat.id, 14, answer)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("15. В каком формате вы работаете?")
    await state.set_state(SurveyStates.QUESTION_15_FIELD)

async def process_question_15(message: types.Message, state: FSMContext):
    field = message.text.strip()
    await save_answer(message.chat.id, 15, field)
    await message.answer("16. В какой сфере вы работаете?")
    await state.set_state(SurveyStates.QUESTION_16_JOB_CHANGE)

async def process_question_16(message: types.Message, state: FSMContext):
    answer = message.text.strip()
    await save_answer(message.chat.id, 16, answer)
    data = await state.get_data()
    success = await save_to_google_sheets(message.chat.id)
    if success:
        await message.answer(
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
        await message.answer("Теперь выберите будний день для ведения дневника времени:", reply_markup=get_weekdays_keyboard())
    else:
        await message.answer(
            f"{data['user_name']}, спасибо за ответы!\n"
            "К сожалению, произошла ошибка при сохранении данных. "
            "Пожалуйста, сообщите об этом администратору."
        )
    await state.set_state(SurveyStates.SELECT_WEEKDAY)

async def process_weekday_selection(callback: types.CallbackQuery, state: FSMContext):
    day_map = {
        "day_monday": "Понедельник",
        "day_tuesday": "Вторник",
        "day_wednesday": "Среда",
        "day_thursday": "Четверг",
        "day_friday": "Пятница"
    }
    selected_day = day_map.get(callback.data, "Неизвестный день")
    with sqlite3.connect("research_bot.db") as conn:
        conn.execute("UPDATE participants SET weekday = ? WHERE chat_id = ?", (selected_day, callback.message.chat.id))
    await callback.answer(f"Вы выбрали {selected_day} как будний день")
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("Теперь выберите выходной день:", reply_markup=get_weekend_keyboard())
    await state.set_state(SurveyStates.SELECT_WEEKEND)

async def process_weekend_selection(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_name = data.get('user_name', '')
    day_map = {
        "day_saturday": "Суббота",
        "day_sunday": "Воскресенье"
    }
    selected_day = day_map.get(callback.data, "Неизвестный день")
    with sqlite3.connect("research_bot.db") as conn:
        conn.execute("UPDATE participants SET weekend = ? WHERE chat_id = ?", (selected_day, callback.message.chat.id))
        cursor = conn.cursor()
        cursor.execute("SELECT weekday, weekend FROM participants WHERE chat_id = ?", (callback.message.chat.id,))
        days = cursor.fetchone()
        await state.update_data(selected_weekday=days[0], selected_weekend=days[1])
    await callback.answer(f"Вы выбрали {selected_day} как выходной день")
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("Перейдем дальше", reply_markup=get_understand_keyboard())
    await state.set_state(SurveyStates.INSTRUCTION_1)

async def process_instruction_1(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    data = await state.get_data()
    today = datetime.now(pytz.timezone('Europe/Moscow')).date()
    weekday_map = {
        "Понедельник": 0, "Вторник": 1, "Среда": 2, "Четверг": 3,
        "Пятница": 4, "Суббота": 5, "Воскресенье": 6
    }
    weekday_num = weekday_map[data['selected_weekday']]
    next_weekday = today + timedelta((weekday_num - today.weekday()) % 7)
    if next_weekday <= today:
        next_weekday += timedelta(weeks=1)
    following_weekday = next_weekday + timedelta(weeks=1)
    weekend_num = weekday_map[data['selected_weekend']]
    next_weekend = today + timedelta((weekend_num - today.weekday()) % 7)
    if next_weekend <= today:
        next_weekend += timedelta(weeks=1)
    following_weekend = next_weekend + timedelta(weeks=1)
    with sqlite3.connect("research_bot.db") as conn:
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
                     ))
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

async def process_instruction_2(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "В ходе дневника вам нужно будет последовательно описать, как проходит ваш день, с разбивкой по 20-минутным промежуткам. "
        "Настоятельно прошу вас заполнять дневник несколько раз за день (например, два раза: в обед и вечером перед сном), "
        "чтобы ничего не упустить.",
        reply_markup=get_understand_keyboard()
    )
    await state.set_state(SurveyStates.INSTRUCTION_3)

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

async def process_instruction_4(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    data = await state.get_data()
    await callback.message.answer(
        f"Если у вас после прочтения инструкции возникли вопросы, пожалуйста, напишите мне в Telegram: @moi_e_va или в WhatsApp: 89629574866.\n\n"
        f"Еще раз благодарю вас, {data['user_name']}, за участие в исследовании. Удачи в заполнении дневников!"
    )
    await state.set_state(SurveyStates.FINISHED)

def register_handlers(dp: Dispatcher):
    dp.message.register(cmd_start, F.text == "/start")
    dp.callback_query.register(handle_start_survey, F.data == "start_survey", SurveyStates.WAITING_FOR_START)
    dp.message.register(process_user_name, SurveyStates.ASKING_NAME)
    dp.message.register(process_question_1, SurveyStates.QUESTION_1_AGE)
    dp.callback_query.register(process_question_2, F.data.in_(["yes", "no"]), SurveyStates.QUESTION_2_HUSBAND)
    dp.message.register(process_question_3, SurveyStates.QUESTION_3_CHILDREN_COUNT)
    dp.message.register(process_question_4, SurveyStates.QUESTION_4_CHILD_AGE)
    dp.message.register(process_question_5, SurveyStates.QUESTION_5_FAMILY)
    dp.callback_query.register(process_question_6, F.data.startswith("income_"), SurveyStates.QUESTION_6_INCOME)
    dp.message.register(process_question_7, SurveyStates.QUESTION_7_HELP)
    dp.callback_query.register(process_question_8, F.data.startswith("location_"), SurveyStates.QUESTION_8_LOCATION)
    dp.message.register(process_question_8a, SurveyStates.QUESTION_8A_LOCATION_DETAIL)
    dp.callback_query.register(process_question_9, F.data.in_(["yes", "no"]), SurveyStates.QUESTION_9_KINDERGARTEN)
    dp.callback_query.register(process_question_10, F.data.in_(["yes", "no"]), SurveyStates.QUESTION_10_NANNY)
    dp.callback_query.register(process_question_11, F.data.in_(["yes", "no"]), SurveyStates.QUESTION_11_ACTIVITIES)
    dp.callback_query.register(process_question_12, F.data.in_(["yes", "no"]), SurveyStates.QUESTION_12_EDUCATION)
    dp.message.register(process_question_13_field, SurveyStates.QUESTION_13_EDUCATION_DETAILS)
    dp.message.register(process_question_13_level, SurveyStates.QUESTION_13_EDUCATION_LEVEL)
    dp.message.register(process_question_13_year, SurveyStates.QUESTION_13_EDUCATION_YEAR)
    dp.callback_query.register(process_question_14, F.data.startswith("schedule_"), SurveyStates.QUESTION_14_SCHEDULE)
    dp.message.register(process_question_15, SurveyStates.QUESTION_15_FIELD)
    dp.message.register(process_question_16, SurveyStates.QUESTION_16_JOB_CHANGE)
    dp.callback_query.register(process_weekday_selection, F.data.startswith("day_"), SurveyStates.SELECT_WEEKDAY)
    dp.callback_query.register(process_weekend_selection, F.data.startswith("day_"), SurveyStates.SELECT_WEEKEND)
    dp.callback_query.register(process_instruction_1, F.data == "understand", SurveyStates.INSTRUCTION_1)
    dp.callback_query.register(process_instruction_2, F.data == "understand", SurveyStates.INSTRUCTION_2)
    dp.callback_query.register(process_instruction_3, F.data == "understand", SurveyStates.INSTRUCTION_3)
    dp.callback_query.register(process_instruction_4, F.data == "understand", SurveyStates.INSTRUCTION_4)