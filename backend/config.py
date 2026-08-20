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
        try:
            _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
            _client.admin.command('ping')
            db = _client[MONGO_DB_NAME]
            chats_collection = db["chats"]
            messages_collection = db["messages"]
        except Exception:
            # MongoDB not available, use in-memory fallback
            db = None
            chats_collection = None
            messages_collection = None


def get_db():
    global db
    if db is None:
        init_mongo()
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
        "- Перед вызовом инструмента кратко опиши, что собираешься сделать и почему.\n"
        "- Стиль: краткий и чёткий."
    ),
    retries=2
)
