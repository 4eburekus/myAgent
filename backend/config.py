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
        "- Общайся на русском языке.\n"
        "- Используй инструмент 'calculate' для всех вычислений.\n"
        "- Сохраняй ключевую информацию в 'agent_notes'.\n"
        "- В начале разговора, когда понял тему, вызови инструмент 'set_chat_title' с коротким названием чата (3-6 слов), отражающим суть. Не вызывай его повторно в этом же чате.\n"
        "- Для работы с файлами используй инструмент 'run_console_command' (ls, cat, cp, mv, mkdir, touch, echo, find, grep, wc, head, tail, pwd, date, uptime, chmod, chown, touch, ln, du, stat, file, readlink, basename, dirname). Все файлы строго внутри /app/workspace.\n"
        "- Перед вызовом инструмента кратко опиши, что собираешься сделать и почему.\n"
        "- Стиль: краткий и чёткий."
    ),
    retries=2  # количество повторных попыток при ошибке
)