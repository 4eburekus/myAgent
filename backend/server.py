from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json
import uuid
from datetime import datetime

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import agent, AssistantDeps, get_db, chats_collection, messages_collection
import tools  # noqa: register tools

from pydantic_ai.messages import ModelRequest, ModelResponse, UserPromptPart, TextPart

app = FastAPI(title="AI Assistant Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- DTOs ----
class ChatCreate(BaseModel):
    name: str = "Новый чат"


class ChatRename(BaseModel):
    name: str


class ChatMessage(BaseModel):
    content: str
    role: str = "user"


class MessageModel(BaseModel):
    id: str
    role: str
    content: str
    created_at: str


class ChatModel(BaseModel):
    id: str
    name: str
    messages: List[MessageModel] = []
    updated_at: str
    created_at: str


# ---- WebSocket: real-time chat streaming ----
@app.websocket("/ws/{chat_id}")
async def websocket_endpoint(websocket: WebSocket, chat_id: str):
    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)

            if data.get("type") == "message":
                # Get or create chat
                db = get_db()
                chat = db["chats"].find_one({"_id": chat_id})
                if not chat:
                    chat = {
                        "_id": chat_id,
                        "name": "Новый чат",
                        "messages": [],
                        "notes": [],
                        "created_at": datetime.utcnow().isoformat(),
                        "updated_at": datetime.utcnow().isoformat()
                    }
                    db["chats"].insert_one(chat)

                # история теперь передаётся агенту штатным механизмом 
                # pydantic-ai — через параметр message_history. 
                # Для каждого сохранённого сообщения строится объект истории
                history: list = []
                for m in chat.get("messages", []):
                    if m.get("role") == "user":
                        history.append(ModelRequest(parts=[UserPromptPart(content=m["content"])]))
                    elif m.get("role") == "assistant":
                        history.append(ModelResponse(parts=[TextPart(content=m["content"])]))

                deps = AssistantDeps(chat_id=chat_id)
                try:
                    result = await agent.run(
                        data["content"],
                        deps=deps,
                        message_history=history,
                    )

                    # Stream agent internals back as events
                    for msg in result.new_messages():
                        for part in msg.parts:
                            # --- thought / reasoning ---
                            if hasattr(part, "provider_details") and part.provider_details:
                                raw_text = part.provider_details.get("raw_content")
                                if raw_text:
                                    await websocket.send_json({
                                        "type": "thought",
                                        "content": "".join(raw_text).strip(),
                                    })

                            # --- tool call / result ---
                            if hasattr(part, "tool_name"):
                                if hasattr(part, "args"):
                                    await websocket.send_json({
                                        "type": "tool_call",
                                        "name": part.tool_name,
                                        "args": str(part.args),
                                    })
                                if hasattr(part, "content"):
                                    await websocket.send_json({
                                        "type": "tool_result",
                                        "name": part.tool_name,
                                        "content": str(part.content),
                                    })

                    # --- final answer ---
                    await websocket.send_json({
                        "type": "final",
                        "content": result.output,
                    })

                    # Save to DB
                    chat["messages"].append({
                        "role": "user",
                        "content": data["content"],
                        "created_at": datetime.utcnow().isoformat()
                    })
                    chat["messages"].append({
                        "role": "assistant",
                        "content": result.output,
                        "created_at": datetime.utcnow().isoformat()
                    })
                    chat["updated_at"] = datetime.utcnow().isoformat()
                    db["chats"].update_one(
                        {"_id": chat_id},
                        {"$set": {"messages": chat["messages"], "updated_at": chat["updated_at"]}}
                    )

                except Exception as exc:
                    await websocket.send_json({"type": "error", "content": str(exc)})

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_json({"type": "error", "content": str(exc)})
        except Exception:
            pass


# ---- REST: chat management ----
@app.get("/api/chats")
def list_chats():
    """Получить список всех чатов"""
    db = get_db()
    chats = list(db["chats"].find().sort("updated_at", -1))
    return [
        {
            "id": c["_id"],
            "name": c.get("name", "Новый чат"),
            "updated_at": c.get("updated_at", ""),
            "message_count": len(c.get("messages", []))
        }
        for c in chats
    ]


@app.get("/api/chats/{chat_id}")
def get_chat(chat_id: str):
    """Получить чат по ID"""
    db = get_db()
    chat = db["chats"].find_one({"_id": chat_id})
    if not chat:
        raise HTTPException(404, "Chat not found")
    return {
        "id": chat["_id"],
        "name": chat.get("name", "Новый чат"),
        "messages": chat.get("messages", []),
        "updated_at": chat.get("updated_at", ""),
        "created_at": chat.get("created_at", "")
    }


@app.post("/api/chats", status_code=201)
def create_chat(body: ChatCreate):
    """Создать новый чат"""
    db = get_db()
    chat_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    chat = {
        "_id": chat_id,
        "name": body.name,
        "messages": [],
        "created_at": now,
        "updated_at": now
    }
    db["chats"].insert_one(chat)
    return chat


@app.put("/api/chats/{chat_id}/rename")
def rename_chat(chat_id: str, body: ChatRename):
    """Переименовать чат"""
    db = get_db()
    chat = db["chats"].find_one({"_id": chat_id})
    if not chat:
        raise HTTPException(404, "Chat not found")
    chat["name"] = body.name
    chat["updated_at"] = datetime.utcnow().isoformat()
    db["chats"].update_one(
        {"_id": chat_id},
        {"$set": {"name": body.name, "updated_at": chat["updated_at"]}}
    )
    return chat


@app.delete("/api/chats/{chat_id}")
def delete_chat(chat_id: str):
    """Удалить чат"""
    db = get_db()
    chat = db["chats"].delete_one({"_id": chat_id})
    if chat.deleted_count == 0:
        raise HTTPException(404, "Chat not found")
    return {"ok": True}


@app.get("/api/messages/{chat_id}")
def get_messages(chat_id: str):
    """Получить историю сообщений чата"""
    db = get_db()
    chat = db["chats"].find_one({"_id": chat_id})
    if not chat:
        raise HTTPException(404, "Chat not found")
    return chat.get("messages", [])
