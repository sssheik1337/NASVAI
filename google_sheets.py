import logging
import sqlite3
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import GOOGLE_SHEETS_CREDENTIALS_FILE, SPREADSHEET_ID
from datetime import datetime

logger = logging.getLogger(__name__)

def init_google_sheets():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_SHEETS_CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds)
        return client.open_by_key(SPREADSHEET_ID).sheet1
    except FileNotFoundError as e:
        logger.error(f"Файл учетных данных не найден: {GOOGLE_SHEETS_CREDENTIALS_FILE}, ошибка: {e}")
        raise
    except Exception as e:
        logger.error(f"Ошибка при инициализации Google Sheets: {e}")
        raise

async def save_to_google_sheets(chat_id: int):
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_SHEETS_CREDENTIALS_FILE, scope)
            client = gspread.authorize(creds)
            try:
                spreadsheet = client.open_by_key(SPREADSHEET_ID)
                worksheet = spreadsheet.sheet1
            except gspread.SpreadsheetNotFound:
                logger.error(f"Таблица с ID {SPREADSHEET_ID} не найдена")
                return False
            except Exception as e:
                logger.error(f"Ошибка при открытии таблицы: {e}")
                return False
        except FileNotFoundError as e:
            logger.error(f"Файл учетных данных не найден: {GOOGLE_SHEETS_CREDENTIALS_FILE}, ошибка: {e}")
            return False
        except Exception as e:
            logger.error(f"Ошибка авторизации в Google API: {e}")
            return False

        with sqlite3.connect("research_bot.db") as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT name, username FROM participants WHERE chat_id = ?', (chat_id,))
            user_data = cursor.fetchone()
            cursor.execute('SELECT question, answer FROM survey_answers WHERE chat_id = ? ORDER BY question', (chat_id,))
            answers = cursor.fetchall()

        if not user_data or not answers:
            logger.error("Не найдены данные пользователя или ответы")
            return False

        name, username = user_data
        row_data = [str(datetime.now()), name, f"@{username}" if username else "", *[answer for _, answer in sorted(answers, key=lambda x: x[0])]]

        try:
            worksheet.append_row(row_data)
            logger.info("Данные анкеты успешно сохранены в Google Sheets")
            return True
        except Exception as e:
            logger.error(f"Ошибка при добавлении строки: {e}")
            return False
    except Exception as e:
        logger.error(f"Общая ошибка при сохранении в Google Sheets: {e}")
        return False