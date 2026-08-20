from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import uuid
from datetime import datetime

app = FastAPI(title="ChatList Service")

# In-memory storage (for now, later MongoDB)
chats_db: dict[str, dict] = {}


class ChatCreate(BaseModel):
    name: str


class ChatRename(BaseModel):
    name: str


@app.get("/api/chats")
def list_chats():
    return [
        {"id": c["id"], "name": c["name"], "updated_at": c["updated_at"]}
        for c in chats_db.values()
    ]


@app.post("/api/chats", status_code=201)
def create_chat(body: ChatCreate):
    chat_id = str(uuid.uuid4())[:8]
    now = datetime.utcnow().isoformat()
    chats_db[chat_id] = {
        "id": chat_id,
        "name": body.name,
        "updated_at": now,
    }
    return chats_db[chat_id]


@app.put("/api/chats/{chat_id}/rename")
def rename_chat(chat_id: str, body: ChatRename):
    chat = chats_db.get(chat_id)
    if not chat:
        raise HTTPException(404, "Chat not found")
    chat["name"] = body.name
    chat["updated_at"] = datetime.utcnow().isoformat()
    return chat


@app.delete("/api/chats/{chat_id}")
def delete_chat(chat_id: str):
    chat = chats_db.pop(chat_id, None)
    if not chat:
        raise HTTPException(404, "Chat not found")
    return {"ok": True}
