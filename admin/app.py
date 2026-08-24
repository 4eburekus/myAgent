# admin/app.py — прямое чтение чатов из MongoDB (без прокси на backend)
import os
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "myagent")

_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = _client[MONGO_DB_NAME]
chats_collection = db["chats"]

app = FastAPI(title="Chat Admin (direct Mongo)")


def _serialize_chat(chat) -> dict:
    """Преобразовать документ Mongo в JSON-ответ (id вместо _id, строковые даты)."""
    return {
        "id": chat.get("_id"),
        "name": chat.get("name", "Новый чат"),
        "messages": chat.get("messages", []),
        "created_at": chat.get("created_at", ""),
        "updated_at": chat.get("updated_at", ""),
    }


@app.get("/")
def index():
    return FileResponse("index.html")


@app.get("/api/chats")
def list_chats():
    """Список чатов напрямую из Mongo, сортировка по updated_at desc."""
    chats = list(chats_collection.find().sort("updated_at", -1))
    return [
        {
            "id": c.get("_id"),
            "name": c.get("name", "Новый чат"),
            "updated_at": c.get("updated_at", ""),
            "message_count": len(c.get("messages", [])),
        }
        for c in chats
    ]


@app.get("/api/chats/{chat_id}")
def get_chat(chat_id: str):
    """Один чат (включая сообщения) напрямую из Mongo."""
    chat = chats_collection.find_one({"_id": chat_id})
    if not chat:
        raise HTTPException(404, "Chat not found")
    return _serialize_chat(chat)


@app.post("/api/chats", status_code=201)
def create_chat():
    """Создать новый чат напрямую в Mongo."""
    import uuid
    chat_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    chat = {
        "_id": chat_id,
        "name": "Новый чат",
        "messages": [],
        "created_at": now,
        "updated_at": now,
    }
    chats_collection.insert_one(chat)
    return _serialize_chat(chat)


@app.put("/api/chats/{chat_id}/rename")
def rename_chat(chat_id: str, body: dict = None):
    """Переименовать чат напрямую в Mongo."""
    if body is None:
        body = {}
    name = body.get("name") or "Новый чат"
    res = chats_collection.update_one(
        {"_id": chat_id},
        {"$set": {"name": name, "updated_at": datetime.utcnow().isoformat()}},
    )
    if res.matched_count == 0:
        raise HTTPException(404, "Chat not found")
    return _serialize_chat(chats_collection.find_one({"_id": chat_id}))


@app.delete("/api/chats/{chat_id}")
def delete_chat(chat_id: str):
    """Удалить чат напрямую из Mongo."""
    res = chats_collection.delete_one({"_id": chat_id})
    if res.deleted_count == 0:
        raise HTTPException(404, "Chat not found")
    return {"ok": True}


@app.get("/api/messages/{chat_id}")
def get_messages(chat_id: str):
    """Сообщения чата напрямую из Mongo."""
    chat = chats_collection.find_one({"_id": chat_id})
    if not chat:
        raise HTTPException(404, "Chat not found")
    return chat.get("messages", [])
