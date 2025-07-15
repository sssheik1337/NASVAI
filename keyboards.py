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
            [InlineKeyboardButton(text="Полный рабочий день (фиксированный график)", callback_data="schedule_full_fixed")],
            [InlineKeyboardButton(text="Полный рабочий день (гибкий график)", callback_data="schedule_full_flex")],
            [InlineKeyboardButton(text="Неполный рабочий день", callback_data="schedule_part")],
            [InlineKeyboardButton(text="Временная / проектная работа", callback_data="schedule_temp")]
        ]
    )

def get_work_format_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="В офисе/на территории работодателя", callback_data="format_office")],
            [InlineKeyboardButton(text="Удалённо (из дома или другого места)", callback_data="format_remote")],
            [InlineKeyboardButton(text="Гибридный формат", callback_data="format_hybrid")]
        ]
    )

def get_satisfaction_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Полностью удовлетворена", callback_data="satisfaction_full")],
            [InlineKeyboardButton(text="Скорее удовлетворена", callback_data="satisfaction_mostly")],
            [InlineKeyboardButton(text="Затрудняюсь ответить", callback_data="satisfaction_neutral")],
            [InlineKeyboardButton(text="Скорее не удовлетворена", callback_data="satisfaction_partly")],
            [InlineKeyboardButton(text="Совершенно не удовлетворена", callback_data="satisfaction_none")]
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

def get_same_location_buttons():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Я была там же", callback_data="loc_same")],
            [InlineKeyboardButton(text="Я была в другом месте", callback_data="loc_different")]
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

def get_same_companions_buttons():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Я была с теми же людьми", callback_data="comp_same")],
            [InlineKeyboardButton(text="Я была с другими людьми", callback_data="comp_different")]
        ]
    )

def get_childcare_buttons():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Ситуация не менялась", callback_data="childcare_same")],
            [InlineKeyboardButton(text="Другой человек", callback_data="childcare_different")]
        ]
    )

def get_help_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Полная инструкция", url="https://docs.google.com/document/d/1rjZTpUahA0Zot-qprL93ZQZi7xKZ7qtgQPoa7RsMtnI/edit?usp=sharing")],
            [InlineKeyboardButton(text="Telegram: @moi_e_va", url="https://t.me/moi_e_va")],
            [InlineKeyboardButton(text="WhatsApp: +7(962)957-48-66", url="https://wa.me/+79629574866")]
        ]
    )

def get_reminder_response_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Да, я заполню завтра", callback_data="remind_ok")],
            [InlineKeyboardButton(text="Нет, я хочу это сделать в другой день", callback_data="remind_later")]
        ]
    )

def get_start_diary_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Начать дневник", callback_data="start_diary")]
        ]
    )

def get_same_location_buttons():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Я была там же", callback_data="loc_same")],
        [InlineKeyboardButton(text="Я была в другом месте", callback_data="loc_different")]
    ])
    return keyboard

def get_same_companions_buttons():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Я была с теми же людьми", callback_data="comp_same")],
        [InlineKeyboardButton(text="Я была с другими людьми", callback_data="comp_different")]
    ])
    return keyboard

def get_childcare_buttons():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ситуация не менялась", callback_data="childcare_same")],
        [InlineKeyboardButton(text="Другой человек", callback_data="childcare_different")]
    ])
    return keyboard