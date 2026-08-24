# - FastAPI: создание веб-приложения
# - WebSocket: поддержка WebSocket-соединений (реальное время)
# - WebSocketDisconnect: исключение при разрыве WebSocket-соединения
# - HTTPException: ошибка HTTP для REST API (404)
# - Query: параметр запроса URL (query parameter)
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware # CORS позволяет фронтенду обращаться к бэкенду с другого домена/порта
from pydantic import BaseModel # BaseModel позволяет FastAPI автоматически валидировать и сериализовать JSON
from typing import List, Optional # List — для указания списков (например, List[MessageModel]) Optional — для указания "может быть None" (например, Optional[str])
import json
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import agent, AssistantDeps, get_db, chats_collection, messages_collection
import tools
# типы из pydantic_ai.messages     запросLLM      ответLLM     пользЗапрос    текстовая часть ответа
from pydantic_ai.messages import ModelRequest, ModelResponse, UserPromptPart, TextPart

# title — название, которое отображается в Swagger-документации
app = FastAPI(title="AI Assistant Backend")
# Добавляем middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], #разрешает запросы с любого домена (для разработки)
    allow_methods=["*"], #разрешает все HTTP-методы (GET, POST, PUT, DELETE)
    allow_headers=["*"], #разрешает все заголовки (Authorization, Content-Type и т.д.)
)


# Модель для создания чата: содержит название чата
class ChatCreate(BaseModel):
    name: str = "Новый чат"


# Модель для переименования чата: содержит новое название
class ChatRename(BaseModel):
    name: str


# Модель для сообщения: содержит текст и роль (user/assistant)
class ChatMessage(BaseModel):
    content: str
    role: str = "user"


# Модель для сообщения в истории чата
class MessageModel(BaseModel):
    id: str  # уникальный ID сообщения
    role: str
    content: str
    created_at: str  # время создания (ISO-формат)


# Модель для чата: содержит все сообщения и метаданные
class ChatModel(BaseModel):
    id: str  # ID чата
    name: str
    messages: List[MessageModel] = []  # список сообщений (по умолчанию пустой)
    updated_at: str  # время последнего обновления
    created_at: str  # время создания


# Определяем WebSocket-эндпоинт: /ws/{chat_id} — путь с параметром chat_id (уникальный ID чата)
@app.websocket("/ws/{chat_id}")
async def websocket_endpoint(websocket: WebSocket, chat_id: str):
    # Принимаем входящее WebSocket-соединение, без этого вызова клиент не получит ответ "принято"
    await websocket.accept()
    
    try:
        while True:  # обрабатываем все входящие сообщения
            # Получаем текст от клиента (JSON-строка)
            raw = await websocket.receive_text()
            # Парсим JSON-строку в Python-словарь
            data = json.loads(raw)
            
            if data.get("type") == "message":
                db = get_db()
                # Ищем чат по _id (это chat_id из параметра WebSocket-URL) уникальный, из контекста Chainlit
                chat = db["chats"].find_one({"_id": chat_id})
                # Если чат не найден
                if not chat:
                    chat = {
                        "_id": chat_id,
                        "name": "Новый чат",
                        "messages": [],
                        "notes": [],
                        "created_at": datetime.utcnow().isoformat(),
                        "updated_at": datetime.utcnow().isoformat()
                    }
                    # Вставляем новый чат в коллекцию MongoDB
                    db["chats"].insert_one(chat)
                
                # Сборка истории диалога для агента
                history: list = []
                # Проходим по всем сообщениям чата из MongoDB
                for m in chat.get("messages", []):
                    if m.get("role") == "user":
                        history.append(ModelRequest(parts=[UserPromptPart(content=m["content"])]))
                    elif m.get("role") == "assistant":
                        history.append(ModelResponse(parts=[TextPart(content=m["content"])]))
                
                # Создаём зависимости агента с ID чата
                deps = AssistantDeps(chat_id=chat_id)
                try:
                    result = await agent.run(
                        data["content"], #текущее сообщение от пользователя
                        deps=deps,
                        message_history=history, #вся история диалога для контекста
                    )
                    
                    # Собираем все вызовы инструментов из результатов агента
                    tool_calls = [
                        # Для каждого сообщения в result.new_messages() берём все части (parts)
                        # Проверяем, что часть имеет attribute "tool_name" (это инструмент)
                        # Собираем кортеж (tool_name, args)
                        (p.tool_name, str(p.args) if hasattr(p, "args") else "")
                        for msg in result.new_messages()
                        for p in msg.parts
                        if hasattr(p, "tool_name")
                    ]
                    # сколько раз был вызван run_console_command
                    console_calls_count = sum(1 for name, _ in tool_calls if name == "run_console_command")
                    
                    # Если были вызовы консоли — обновляем счётчик в чате
                    if console_calls_count:
                        chat["console_calls"] = chat.get("console_calls", 0) + console_calls_count
                        if chat["console_calls"] > 5:
                            chat["console_calls"] = 5
                    
                    # Проходим по всем новым сообщениям от агента
                    for msg in result.new_messages():
                        for part in msg.parts:
                            # === Thought/Reasoning (мышление) ===
                            if hasattr(part, "provider_details") and part.provider_details:
                                # Получаем "сырой" текст размышлений от провайдера (LLM)
                                raw_text = part.provider_details.get("raw_content")
                                # Если есть текст — отправляем его клиенту как событие "thought"
                                if raw_text:
                                    await websocket.send_json({
                                        "type": "thought",  # тип события: размышление
                                        "content": "".join(raw_text).strip()  # текст размышлений
                                    })
                            
                            # === Tool Call / Result (вызов/результат инструмента) ===
                            if hasattr(part, "tool_name"):
                                # Если есть аргументы — отправляем событие "tool_call"
                                if hasattr(part, "args"):
                                    await websocket.send_json({
                                        "type": "tool_call",  # тип события: вызов инструмента
                                        "name": part.tool_name,  # имя инструмента (например, "run_console_command")
                                        "args": str(part.args)  # аргументы (строка)
                                    })
                                
                                # Если есть контент — отправляем событие "tool_result"
                                if hasattr(part, "content"):
                                    await websocket.send_json({
                                        "type": "tool_result",  # тип события: результат инструмента
                                        "name": part.tool_name,  # имя инструмента
                                        "content": str(part.content)  # результат выполнения
                                    })
                    
                    # === Финальный ответ от агента ===
                    # Отправляем финальный результат как событие "final"
                    await websocket.send_json({
                        "type": "final",  # тип события: финальный ответ
                        "content": result.output  # финальный текст от агента
                    })
                    # === Сохранение в базу данных ===
                    # Добавляем сообщение пользователя в историю
                    chat["messages"].append({
                        "role": "user",  # роль: пользователь
                        "content": data["content"],  # текст сообщения
                        "created_at": datetime.utcnow().isoformat()  # время создания
                    })
                    # Добавляем сообщение ассистента в историю
                    chat["messages"].append({
                        "role": "assistant",  # роль: ассистент
                        "content": result.output,  # текст ответа
                        "created_at": datetime.utcnow().isoformat()  # время создания
                    })
                    # Обновляем время последнего обновления чата
                    chat["updated_at"] = datetime.utcnow().isoformat()
                    # Сохраняем обновлённую историю чата в MongoDB
                    db["chats"].update_one(
                        {"_id": chat_id},  # ищем чат по _id
                        {"$set": {  # операция: установить поля
                            "messages": chat["messages"],  # обновляем список сообщений
                            "updated_at": chat["updated_at"]  # обновляем время обновления
                        }}
                    )
                
                except Exception as exc:
                    await websocket.send_json({"type": "error", "content": str(exc)})
    
    except WebSocketDisconnect:  # если клиент разорвал соединение - закрыл вкладку
        pass
    except Exception as exc:  # любая другая ошибка
        try:
            await websocket.send_json({"type": "error", "content": str(exc)})
        except Exception:
            pass



@app.get("/api/chats")
def list_chats():
    """Получить список всех чатов"""
    db = get_db()
    
    # Запрашиваем все чаты, сортируя по updated_at (обновлению) в порядке убывания
    # Новые чаты (или чаты с последними сообщениями) — в начале
    chats = list(db["chats"].find().sort("updated_at", -1))
    return [
        {
            "id": c["_id"],
            "name": c.get("name", "Новый чат"),
            "updated_at": c.get("updated_at", ""),
            "message_count": len(c.get("messages", []))
        }
        for c in chats  # для каждого чата в списке
    ]


@app.get("/api/chats/{chat_id}")
def get_chat(chat_id: str):
    """Получить чат по ID"""
    db = get_db()
    # Ищем чат по _id
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
    # Генерируем уникальный ID для нового чата
    chat_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    # Создаём документ чата
    chat = {
        "_id": chat_id,
        "name": body.name,
        "messages": [],
        "created_at": now,
        "updated_at": now
    }
    # Вставляем чат в MongoDB
    db["chats"].insert_one(chat)
    # Возвращаем созданный чат (201 Created)
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
    # Обновляем чат в MongoDB
    db["chats"].update_one(
        {"_id": chat_id},  # ищем по _id
        {"$set": {  # операция: установить поля
            "name": body.name,  # новое название
            "updated_at": chat["updated_at"]  # время обновления
        }}
    )
    # Возвращаем обновлённый чат
    return chat


@app.delete("/api/chats/{chat_id}")
def delete_chat(chat_id: str):
    """Удалить чат"""
    db = get_db()
    chat = db["chats"].delete_one({"_id": chat_id})
    if chat.deleted_count == 0:
        raise HTTPException(404, "Chat not found")
    # Возвращаем подтверждение удаления
    return {"ok": True}


@app.get("/api/messages/{chat_id}")
def get_messages(chat_id: str):
    """Получить историю сообщений чата"""
    db = get_db()
    chat = db["chats"].find_one({"_id": chat_id})
    if not chat:
        raise HTTPException(404, "Chat not found")
    # Возвращаем список сообщений (без лишних полей)
    return chat.get("messages", [])