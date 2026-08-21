import os
from dataclasses import dataclass, field
from typing import List
from pydantic_ai import Agent

os.environ["OPENAI_BASE_URL"] = os.getenv("OPENAI_BASE_URL", "http://10.45.0.75:8000/v1")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "myagent")

_client = None
db = None
chats_collection = None
messages_collection = None


def init_mongo():
    global _client, db, chats_collection, messages_collection
    if _client is None:
        from pymongo import MongoClient
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        _client.admin.command('ping')
        db = _client[MONGO_DB_NAME]
        chats_collection = db["chats"]
        messages_collection = db["messages"]


init_mongo()


def get_db():
    return db


@dataclass
class AssistantDeps:
    notes: List[str] = field(default_factory=list)
    chat_id: str = ""


agent = Agent(
    model='openai:RedHatAi/Qwen3.6-35B-A3B-NVFP4',
    deps_type=AssistantDeps,
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
    retries=2
)
