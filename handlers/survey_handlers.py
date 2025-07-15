import logging
import sqlite3
from aiogram import Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.utils.formatting import Bold, as_list, Text
from states import SurveyStates
from keyboards import get_start_keyboard, get_yes_no_keyboard, get_income_keyboard, get_location_keyboard, get_schedule_keyboard, get_work_format_keyboard, get_satisfaction_keyboard, get_weekdays_keyboard, get_weekend_keyboard, get_understand_keyboard, get_help_keyboard
from database import save_answer
from google_sheets import save_to_google_sheets
from datetime import datetime, timedelta
import pytz

logger = logging.getLogger(__name__)

async def cmd_start(message: types.Message, state: FSMContext):
    content = as_list(
        Bold("Здравствуйте ✨"),
        Text("Большое спасибо вам за участие в моем исследовании, посвященном возвращению женщин после декретного отпуска на работу. Все данные, которые вы здесь предоставите, будут полностью анонимными, а в итоговой исследовательской работе будут указаны в обобщенном виде."),
        Text("Как будет проходить исследование:"),
        Text("1. Короткая анкета (18 вопросов о семье/работе, ~5 минут)"),
        Text("2. Дневник времени (2 дня: 1 будний + 1 выходной, каждый дневник займет примерно 40 минут в день)"),
        Text("3. 3 заключительных вопроса о ваших впечатлениях"),
        Text("Спасибо за ваш вклад в развитие социальных исследований! Ваши ответы помогут создать более эффективные программы поддержки для женщин в аналогичной ситуации."),
        Text("Для старта отправьте “Начать”."),
        sep="\n\n"
    )
    await message.answer(**content.as_kwargs(), reply_markup=get_start_keyboard())
    await state.set_state(SurveyStates.WAITING_FOR_START)

async def cmd_help(message: types.Message, state: FSMContext):
    content = as_list(
        Text("Краткая инструкция по дневнику:"),
        Text("1. Сроки: 2 дня (1 будний + 1 выходной) за 2 недели"),
        Text("2. Начало: Укажите время пробуждения (формат 07:30)"),
        Text("3. Заполнение: Детально описывайте 20-мин интервалы:"),
        Text("   - Основные и параллельные действия"),
        Text("   - Даже короткие занятия (от 2-3 минут)"),
        Text("   - Отвечайте на 4 вопроса:"),
        Text("     • ", Bold("Чем вы занимались?"), " → Максимально подробно!"),
        Text("     • ", Bold("Где вы были?")),
        Text("     • ", Bold("С кем вы были?")),
        Text("     • ", Bold("Кто присматривал за вашим ребенком в это время?")),
        Text("4. Лайфхаки:"),
        Text("   • Фиксируйте детали сразу – так проще вспомнить"),
        Text("   • Используйте кнопки ", Bold("Я была там же"), "/", Bold("Я была с теми же людьми"), "/", Bold("Ситуация не менялась"), ", если они релевантны"),
        Text("5. Завершение: Напишите"), Bold("Ночной сон"),
        Text("❓ Полная инструкция и контакты ниже:"),
        sep="\n"
    )
    await message.answer(**content.as_kwargs(), reply_markup=get_help_keyboard())
    await state.set_state(SurveyStates.FINISHED)

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
            logger.info(f"Пользователь {user_name} (chat_id: {message.chat.id}) зарегистрирован")
    except Exception as e:
        logger.error(f"Ошибка сохранения данных пользователя: {e}")
        await message.answer("Произошла ошибка при сохранении данных. Пожалуйста, попробуйте позже.")
        return
    content = as_list(
        Text(f"{user_name}, в качестве первого этапа, предлагаю вам пройти короткую анкету."),
        Text("Она состоит из 18 вопросов о вашей семье, образовании, занятости и поддержке в уходе за ребенком."),
        Text("Заполнение займет около 5 минут. Это поможет мне узнать о вас чуть-чуть побольше, а также облегчит дальнейшие интервью."),
        Text("1. Сколько вам лет?"),
        sep="\n"
    )
    await message.answer(**content.as_kwargs())
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
    content = as_list(
        Text("6. Как вы оцениваете доход своей семьи?"),
        Text("● Высокий - свободно покрываем все расходы, включая путешествия и крупные покупки, откладываем сбережения"),
        Text("● Выше среднего - хватает на комфортную жизнь и развлечения, но дорогие покупки требуют накоплений"),
        Text("● Средний - средств достаточно на основные нужды (еда, жилье, одежда), но на дополнительные траты остаётся мало"),
        Text("● Ниже среднего - денег хватает только на самое необходимое, приходится строго экономить"),
        Text("● Низкий - доходов не хватает на базовые потребности, есть финансовые трудности"),
        sep="\n"
    )
    await message.answer(**content.as_kwargs(), reply_markup=get_income_keyboard())
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
        "schedule_temp": "Временная/проектная работа"
    }
    answer = schedule_map[callback.data]
    await callback.message.answer(f"Вы выбрали: {answer}")
    await save_answer(callback.message.chat.id, 14, answer)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("15. В каком формате вы работаете?", reply_markup=get_work_format_keyboard())
    await state.set_state(SurveyStates.QUESTION_15_FIELD)

async def process_question_15(callback: types.CallbackQuery, state: FSMContext):
    format_map = {
        "format_office": "В офисе/на территории работодателя",
        "format_remote": "Удалённо (из дома или другого места)",
        "format_hybrid": "Гибридный формат"
    }
    answer = format_map[callback.data]
    await callback.message.answer(f"Вы выбрали: {answer}")
    await save_answer(callback.message.chat.id, 15, answer)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("16. В какой сфере вы работаете?")
    await state.set_state(SurveyStates.QUESTION_16_JOB_CHANGE)

async def process_question_16(message: types.Message, state: FSMContext):
    answer = message.text.strip()
    await save_answer(message.chat.id, 16, answer)
    await message.answer("17. Меняли ли вы работу после декретного отпуска?", reply_markup=get_yes_no_keyboard())
    await state.set_state(SurveyStates.QUESTION_17_JOB_CHANGE_POST_MATERNITY)

async def process_question_17(callback: types.CallbackQuery, state: FSMContext):
    answer = "Да" if callback.data == "yes" else "Нет"
    await callback.message.answer(f"Вы выбрали: {answer}")
    await save_answer(callback.message.chat.id, 17, answer)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "18. Насколько вы удовлетворены тем, как прошел ваш выход из декретного отпуска?",
        reply_markup=get_satisfaction_keyboard()
    )
    await state.set_state(SurveyStates.QUESTION_18_SATISFACTION)

async def process_question_18(callback: types.CallbackQuery, state: FSMContext):
    satisfaction_map = {
        "satisfaction_full": "Полностью удовлетворена",
        "satisfaction_mostly": "Скорее удовлетворена",
        "satisfaction_neutral": "Затрудняюсь ответить",
        "satisfaction_partly": "Скорее не удовлетворена",
        "satisfaction_none": "Совершенно не удовлетворена"
    }
    answer = satisfaction_map[callback.data]
    await callback.message.answer(f"Вы выбрали: {answer}")
    await save_answer(callback.message.chat.id, 18, answer)
    await callback.message.edit_reply_markup(reply_markup=None)
    data = await state.get_data()
    success = await save_to_google_sheets(callback.message.chat.id)
    if success:
        content = as_list(
            Text(f"{data['user_name']}, спасибо большое за прохождение анкеты!"),
            Text("Ваши ответы успешно сохранены."),
            Text("В рамках исследования в течение следующих 2 недель вам необходимо будет заполнить дневник времени за 2 дня:"),
            Text("1. 1 будний день (понедельник–пятница)"),
            Text("2. 1 выходной день (суббота или воскресенье)"),
            Text("Как это работает:"),
            Text("● Мы с вами в переписке договорились, в какие дни недели вам нужно заполнять дневник. Заполнять его можно только в них!"),
            Text("● Вы сами решаете, заполнять дневник на следующей неделе или через неделю"),
            Text("● За день до каждого назначенного дня вы получите напоминание о прохождении"),
            sep="\n"
        )
        await callback.message.answer(**content.as_kwargs(), reply_markup=get_understand_keyboard())
        await state.set_state(SurveyStates.INSTRUCTION_1)
    else:
        await callback.message.answer(
            f"{data['user_name']}, спасибо за ответы!\n"
            "К сожалению, произошла ошибка при сохранении данных. "
            "Пожалуйста, сообщите об этом администратору."
        )

async def process_instruction_1(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    content = as_list(
        Text("Напишите, пожалуйста, в какие дни недели мы договорились заполнять дневник?"),
        Text("(Укажите дни через запятую, например, 'Четверг, Воскресенье')")
    )
    await callback.message.answer(**content.as_kwargs())
    await state.set_state(SurveyStates.INSTRUCTION_2)

async def process_instruction_2(message: types.Message, state: FSMContext):
    days = [day.strip().lower() for day in message.text.split(",")]
    if len(days) != 2:
        content = as_list(
            Text("Пожалуйста, укажите ровно два дня недели через запятую (например, 'Четверг, Воскресенье').")
        )
        await message.answer(**content.as_kwargs())
        return
    valid_weekdays = ["понедельник", "вторник", "среда", "четверг", "пятница"]
    valid_weekends = ["суббота", "воскресенье"]
    weekday, weekend = None, None
    original_days = [day.strip() for day in message.text.split(",")]  # Сохраняем оригинальный ввод
    for day in days:
        if day in valid_weekdays:
            weekday = original_days[days.index(day)]  # Используем оригинальный регистр
        elif day in valid_weekends:
            weekend = original_days[days.index(day)]  # Используем оригинальный регистр
    if not weekday or not weekend:
        content = as_list(
            Text("Пожалуйста, укажите один будний день (Понедельник–Пятница) и один выходной (Суббота или Воскресенье)."),
            Text("Попробуйте снова.")
        )
        await message.answer(**content.as_kwargs())
        return
    await state.update_data(selected_weekday=weekday, selected_weekend=weekend)
    with sqlite3.connect("research_bot.db") as conn:
        conn.execute(
            "UPDATE participants SET weekday = ?, weekend = ? WHERE chat_id = ?",
            (weekday, weekend, message.chat.id)
        )
    today = datetime.now(pytz.timezone('Europe/Moscow')).date()
    weekday_map = {
        "понедельник": 0, "вторник": 1, "среда": 2, "четверг": 3,
        "пятница": 4, "суббота": 5, "воскресенье": 6
    }
    weekday_num = weekday_map[weekday.lower()]
    next_weekday = today + timedelta((weekday_num - today.weekday()) % 7)
    if next_weekday <= today:
        next_weekday += timedelta(weeks=1)
    following_weekday = next_weekday + timedelta(weeks=1)
    weekend_num = weekday_map[weekend.lower()]
    next_weekend = today + timedelta((weekend_num - today.weekday()) % 7)
    if next_weekend <= today:
        next_weekend += timedelta(weeks=1)
    following_weekend = next_weekend + timedelta(weeks=1)
    with sqlite3.connect("research_bot.db") as conn:
        conn.execute(
            '''
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
                message.chat.id
            )
        )
    data = await state.get_data()
    content = as_list(
        Text(f"Выбранные для вас дни недели: {weekday} и {weekend}."),
        Text(f"Сегодня - {today.strftime('%d.%m.%Y')}, поэтому вы можете заполнить дневник:"),
        Text(f"📅 {weekday}:"),
        Text(f"- {next_weekday.strftime('%d.%m.%Y')}"),
        Text(f"- {following_weekday.strftime('%d.%m.%Y')}"),
        Text(f"📅 {weekend}:"),
        Text(f"- {next_weekend.strftime('%d.%m.%Y')}"),
        Text(f"- {following_weekend.strftime('%d.%m.%Y')}"),
        sep="\n"
    )
    await message.answer(**content.as_kwargs(), reply_markup=get_understand_keyboard())
    await state.set_state(SurveyStates.INSTRUCTION_3)

async def process_instruction_3(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    content = as_list(
        Text("В ходе дневника вам нужно будет последовательно описать, как проходит ваш день, с разбивкой по 20-минутным промежуткам."),
        Text("Для вашего удобства настоятельно прошу вас заполнять дневник несколько раз за день (например, в обед и вечером перед сном)."),
        Text("Это поможет вам:"),
        Text("● Точнее восстановить детали вашего дня"),
        Text("● Сэкономить ваше время - короткие сессии заполнения менее затратны, чем единый длинный отчет"),
        sep="\n"
    )
    await callback.message.answer(**content.as_kwargs(), reply_markup=get_understand_keyboard())
    await state.set_state(SurveyStates.INSTRUCTION_4)

async def process_instruction_4(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    content = as_list(
        Text(Bold("Как работает заполнение?")),
        Text("Начало дня: Вы указываете время пробуждения в 24-часовом формате через двоеточие (например, 07:30 или 09:23)."),
        Text("Затем, система автоматически определит первый 20-минутный промежуток (например, 07:20–07:40 или 07:40–08:00), который вам нужно будет описать."),
        sep="\n"
    )
    await callback.message.answer(**content.as_kwargs(), reply_markup=get_understand_keyboard())
    await state.set_state(SurveyStates.INSTRUCTION_5)

async def process_instruction_5(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    content = as_list(
        Text("Для каждого промежутка вам зададут 4 вопроса:"),
        Text("1. ", Bold("Чем вы занимались?"), " Пожалуйста, отвечайте на этот вопрос ", Bold("настолько полно насколько возможно"), "."),
        Text("Укажите все действия, которые вы делали, включая те, которые выполнялись одновременно и те, которые заняли у вас совсем немного времени."),
        Text("2. ", Bold("Где вы были?"), " Вам нужно будет написать ваше местоположение (например, дома или на работе)."),
        Text("Если в следующем промежутке вы остаетесь в том же месте, то можно просто нажать на кнопку ", Bold("Я была там же"), "."),
        Text("3. ", Bold("С кем вы были?"), " Вам нужно будет написать, с кем вы были, когда выполняли это действие (например, я была одна, муж, ребенок, мама)."),
        Text("Если в следующем отрывке времени эти люди будут совпадать, то можно просто нажать на кнопку ", Bold("Я была с теми же людьми"), "."),
        Text("4. ", Bold("Кто присматривал за вашим ребенком в это время?"), " Укажите, кто был с вашим ребенком в это время (например, я, бабушка, воспитатели в саду)."),
        Text("Если ситуация идентична предыдущему промежутку, нажмите ", Bold("Ситуация не менялась"), "."),
        sep="\n"
    )
    await callback.message.answer(**content.as_kwargs(), reply_markup=get_understand_keyboard())
    await state.set_state(SurveyStates.INSTRUCTION_6)

async def process_instruction_6(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    content = as_list(
        Text(Bold("Автоматический переход: "),
             "После заполнения одного промежутка бот сразу предложит следующий (например, 08:00–08:20)."),
        Text(Bold("Окончание заполнения: "), "Как только ваш день закончится, напишите ", Bold("Ночной сон"),
             " в ответ на вопрос ", Bold("Чем вы занимались?"), " - дневник закроется."),
        sep="\n"
    )
    await callback.message.answer(**content.as_kwargs(), reply_markup=get_understand_keyboard())
    await state.set_state(SurveyStates.INSTRUCTION_7)

async def process_instruction_7(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    content = as_list(
        Text("Для того, чтобы вы точно поняли суть этого дневника, приводим несколько заполненных примеров."),
        Text("Пример 1: Промежуток 07:40-08:00 (утро)"),
        Text("● ", Bold("Чем вы занимались?")),
        Text("Разбудила сына, помогала ему одеваться. Одновременно разогревала завтрак на плите и упаковывала мужу обед на работу. Отвлеклась на 2 минуты, чтобы ответить на сообщение в родительском чате."),
        Text("● ", Bold("Где вы были?")),
        Text("Дома"),
        Text("● ", Bold("С кем вы были?")),
        Text("Ребенок, Муж"),
        Text("● ", Bold("Кто присматривал за вашим ребенком в это время?")),
        Text("Я сама (готовила его в садик)"),
        sep="\n"
    )
    await callback.message.answer(**content.as_kwargs(), reply_markup=get_understand_keyboard())
    await state.set_state(SurveyStates.INSTRUCTION_8)

async def process_instruction_8(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    content = as_list(
        Text("Пример 2: Промежуток 11:20-11:40 (рабочее время)"),
        Text("● ", Bold("Чем вы занимались?")),
        Text("Активно работала над отчетом на ноутбуке. В середине промежутка прервалась на 5-минутный звонок из детского сада – воспитательница уточнила насчет кружка. Подтвердила, что заберу дочь как обычно после обеда, вернулась к отчету."),
        Text("● ", Bold("Где вы были?")),
        Text("На работе (Участница нажала кнопку ", Bold("Я была там же"), ", так как предыдущие промежутки она тоже была на работе)"),
        Text("● ", Bold("С кем вы были?")),
        Text("Коллеги (Участница нажала кнопку ", Bold("Я была с теми же людьми"), ", так как в предыдущем промежутке она тоже была с коллегами)"),
        Text("● ", Bold("Кто присматривал за вашим ребенком в это время?")),
        Text("Воспитатели в группе детского сада (Участница нажала кнопку ", Bold("Ситуация не менялась"), ", так как ребенок все утро был в саду)"),
        sep="\n"
    )
    await callback.message.answer(**content.as_kwargs(), reply_markup=get_understand_keyboard())
    await state.set_state(SurveyStates.INSTRUCTION_9)

async def process_instruction_9(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    content = as_list(
        Text("Пример 3: Промежуток 18:20-18:30 (после рабочего дня)"),
        Text("● ", Bold("Чем вы занимались?")),
        Text("Гуляла с дочерью на детской площадке во дворе: качала ее на качелях, следила, чтобы не упала. Параллельно просматривала и отвечала на срочные рабочие сообщения в телефоне. Помогла ей слезть с горки."),
        Text("● ", Bold("Где вы были?")),
        Text("На улице (Участница нажала кнопку ", Bold("Я была там же"), ", так как предыдущий промежуток она тоже была на улице)"),
        Text("● ", Bold("С кем вы были?")),
        Text("Ребенок (Участница нажала кнопку ", Bold("Я была с теми же людьми"), ", так как в предыдущем промежутке она тоже была с ребенком)"),
        Text("● ", Bold("Кто присматривал за вашим ребенком в это время?")),
        Text("Я сама гуляла и следила за ней (Участница нажала кнопку ", Bold("Ситуация не менялась"), ", так как в предыдущем промежутке (17:40-18:00) она тоже гуляла с ребенком сама)"),
        sep="\n"
    )
    await callback.message.answer(**content.as_kwargs(), reply_markup=get_understand_keyboard())
    await state.set_state(SurveyStates.INSTRUCTION_10)

async def process_instruction_10(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    data = await state.get_data()
    content = as_list(
        Text("Если у вас после прочтения инструкции возникли вопросы, пожалуйста, напишите мне в Telegram: @moi_e_va или в WhatsApp: 89629574866."),
        Text(f"Еще раз благодарю вас, {data['user_name']}, за участие в исследовании. Удачи в заполнении дневников!✨"),
        sep="\n"
    )
    await callback.message.answer(**content.as_kwargs(), reply_markup=get_help_keyboard())
    await state.set_state(SurveyStates.FINISHED)

def register_handlers(dp: Dispatcher):
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_help, Command("help"))
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
    dp.callback_query.register(process_question_15, F.data.startswith("format_"), SurveyStates.QUESTION_15_FIELD)
    dp.message.register(process_question_16, SurveyStates.QUESTION_16_JOB_CHANGE)
    dp.callback_query.register(process_question_17, F.data.in_(["yes", "no"]), SurveyStates.QUESTION_17_JOB_CHANGE_POST_MATERNITY)
    dp.callback_query.register(process_question_18, F.data.startswith("satisfaction_"), SurveyStates.QUESTION_18_SATISFACTION)
    dp.callback_query.register(process_instruction_1, F.data == "understand", SurveyStates.INSTRUCTION_1)
    dp.message.register(process_instruction_2, SurveyStates.INSTRUCTION_2)
    dp.callback_query.register(process_instruction_3, F.data == "understand", SurveyStates.INSTRUCTION_3)
    dp.callback_query.register(process_instruction_4, F.data == "understand", SurveyStates.INSTRUCTION_4)
    dp.callback_query.register(process_instruction_5, F.data == "understand", SurveyStates.INSTRUCTION_5)
    dp.callback_query.register(process_instruction_6, F.data == "understand", SurveyStates.INSTRUCTION_6)
    dp.callback_query.register(process_instruction_7, F.data == "understand", SurveyStates.INSTRUCTION_7)
    dp.callback_query.register(process_instruction_8, F.data == "understand", SurveyStates.INSTRUCTION_8)
    dp.callback_query.register(process_instruction_9, F.data == "understand", SurveyStates.INSTRUCTION_9)
    dp.callback_query.register(process_instruction_10, F.data == "understand", SurveyStates.INSTRUCTION_10)