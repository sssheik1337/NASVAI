from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_start_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Начать", callback_data="start_survey")]]
    )

def get_yes_no_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Да", callback_data="yes"), InlineKeyboardButton(text="Нет", callback_data="no")]]
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
        inline_keyboard=[[InlineKeyboardButton(text="Понятно", callback_data="understand")]]
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