# Research Bot Project

## Описание
Telegram-бот для проведения исследований о возвращении женщин на работу после декретного отпуска. Включает анкету (18 вопросов), дневники времени (будний и выходной дни) и обратную связь. Данные сохраняются в SQLite и Google Sheets.

## Установка
1. Клонируйте репозиторий: `git clone <repo_url>`
2. Установите зависимости: `pip install -r requirements.txt` (aiogram, pytz, gspread, oauth2client и т.д.)
3. Настройте конфиг: создайте `config.py` с TOKEN, GROUP_ID, SPREADSHEET_ID.
4. Создайте БД: запустите `python main.py` для инициализации SQLite.

## Зависимости
- Python 3.10+
- aiogram
- pytz
- gspread
- oauth2client
- sqlite3 (встроенный)

## Использование
1. Запустите бота: `python main.py`
2. В Telegram: /start для начала анкеты, /start_diary для дневника.
3. Данные сохраняются автоматически в Google Sheets.

## Структура
- `main.py`: Запуск бота.
- `handlers/survey_handlers.py`: Обработка анкеты.
- `handlers/diary_handlers.py`: Обработка дневников.
- `keyboards.py`: Клавиатуры.
- `states.py`: FSM-состояния.
- `database.py`: SQLite-операции.
- `google_sheets.py`: Интеграция с Sheets.

## Лицензия
MIT License.