import os
from dataclasses import dataclass, field  # @dataclass и helper field() для создания dataclass
from typing import List  # для аннотации типов
from pydantic_ai import Agent  # для создания LLM-агента

# Берём значение из переменной окружения OPENAI_BASE_URL в docker-compose.yml
os.environ["OPENAI_BASE_URL"] = os.getenv("OPENAI_BASE_URL", "http://10.45.0.75:8000/v1")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "myagent")

# Переменная для хранения клиента MongoDB (глобальная)
_client = None
# объекта базы данных (глобальная)
db = None
# коллекции чатов (глобальная)
chats_collection = None
# коллекции сообщений (глобальная)
messages_collection = None

def init_mongo():
    """Инициализирует подключение к MongoDB и создаёт глобальные переменные db, chats_collection, messages_collection."""
    global _client, db, chats_collection, messages_collection  # объявляем, что будем использовать глобальные переменные
    if _client is None:  # если клиент ещё не создан
        from pymongo import MongoClient  # импортируем MongoClient
        # Создаём подключение к MongoDB с таймаутом
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        _client.admin.command('ping')
        # Получаем базу данных
        db = _client[MONGO_DB_NAME]
        chats_collection = db["chats"]
        messages_collection = db["messages"]

init_mongo()

# Возвращает объект db
def get_db():
    """Возвращает объект базы данных MongoDB."""
    return db


# @dataclass — создаёт класс для хранения зависимостей агента
@dataclass
class AssistantDeps:
    notes: List[str] = field(default_factory=list)
    chat_id: str = ""

agent = Agent(
    model='openai:RedHatAi/Qwen3.6-35B-A3B-NVFP4',  # модель LLM
    deps_type=AssistantDeps,  # тип зависимостей
    system_prompt=(
        "Ты — ИИ-ассистент. Правила:\n"
        "- Общайся на русском языке;\n"
        "- Стиль: краткий и чёткий;\n"
        "- Использовать доступные тебе инструменты.\n"
        "- Если задачу не получается решить с помощью доступных инструментов, нужно сказать об этом пользователю.\n"
        "Особенности использования инструментов:\n"
        "'calculate' для всех вычислений.\n"
        "'set_chat_title' для изменения названия чата. Вызывать только по просьбе пользователя.\n"
        "'run_console_command' для работы с файлами. (ls, cat, cp, mv, mkdir, touch, echo, find, grep, wc, head, tail, pwd, date, uptime, chmod, chown, touch, ln, du, stat, file, readlink, basename, dirname). Все файлы строго внутри /app/workspace.\n"
        "'fill_docx_fields' для заполнения полей в .docx-шаблоне данными из файла-источника (template, source_file — имена файлов в /app/workspace).\n"
        "'read_excel' для чтения Excel-файлов (.xlsx/.xls), 'create_excel' для создания .xlsx, 'edit_excel' для редактирования Excel (set_cell, add_row, add_column, update_row, clear_cell, rename_sheet).\n"
        "'agent_notes' для сохранения ключевой информации."
    ),
    retries=2  # количество повторных попыток при ошибке
)

# Отдельный агент для семантического сопоставления полей документа с данными из файла.
# Используется внутри инструмента fill_docx_fields. Не имеет инструментов — только текст в/текст out.
agent_matcher = Agent(
    model='openai:RedHatAi/Qwen3.6-35B-A3B-NVFP4',
    system_prompt=(
        "Ты — помощник, который сопоставляет поля документа-шаблона со значениями из файла с данными.\n"
        "Твоя задача — понять, какой смысл у каждого поля (по его подписи и контексту), найти в данных "
        "соответствующее значение и вернуть строго валидный JSON.\n"
        "Правила:\n"
        "- Возвращай ТОЛЬКО JSON-объект вида {\"1\": \"значение\", \"2\": \"значение\", ...} без пояснений.\n"
        "- Ключи — номера полей, значения — текст для вставки.\n"
        "- Если для поля не удалось найти значение, ставь пустую строку.\n"
        "- Сопоставляй по смыслу, а не дословно: 'Имя' может соответствовать 'ФИО', 'Дата рождения' — 'д.р.' и т.п.\n"
        "- Не выдумывай данные — бери только из предоставленного файла."
    ),
    retries=2
)