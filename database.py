import sqlite3
import logging

logger = logging.getLogger(__name__)
DB_FILE = "research_bot.db"

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
                flag INT DEFAULT 0,
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
        logger.error(f"Ошибка сохранения ответа: {e}")