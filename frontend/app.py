# frontend/app.py — Chainlit UI с WebSocket-подключением к бэкенду
import sys  # для работы с путями и т.д.
from pathlib import Path  # для работы с путями файлов
import os  # для работы с окружением и переменными
import json  # для сериализации/десериализации данных

# Добавляем путь к backend-модулю в sys.path, чтобы можно было импортировать 
# из backend (config.py, tools.py и т.д.) из frontend-контекста
sys.path.append(str(Path(__file__).resolve().parent.parent / "backend"))

# фреймворк для чат-интерфейса
import chainlit as cl

# agent (pydantic-ai агент) AssistantDeps (dataclass с параметрами)
# из backend/config.py
from config import agent, AssistantDeps

# все инструменты из tools.py
# noqa: register tools — это noqa-директива, которая говорит линтерам игнорировать 
# это импортирование, потому что оно регистрирует инструменты в системе агента
import tools

# URL для подключения к бэкенду через WebSocket
# Берётся из переменной окружения BACKEND_WS_URL, по умолчанию — ws://localhost:8001/ws
BACKEND_WS_URL = os.getenv("BACKEND_WS_URL", "ws://localhost:8001/ws")

# Декоратор @cl.on_chat_start — запускается, когда пользователь начинает новый чат
@cl.on_chat_start
async def start():
    """Вызывается при старте чата"""
    # chat_id = thread_id из Chainlit: постоянный UUID, хранится в localStorage браузера
    # и переживает перезагрузку страницы. Используется как _id документа в Mongo.
    chat_id = cl.context.session.thread_id
    
    # Сохраняем chat_id в user_session для дальнейшего использования
    cl.user_session.set("chat_id", chat_id)
    # Устанавливаем streaming в False — значит, ничего не идёт сейчас
    cl.user_session.set("streaming", False)
    # Устанавливаем agent в None — агент ещё не инициализирован
    cl.user_session.set("agent", None)
    
    # Отправляем приветственное сообщение пользователю
    # Создаём Message с контентом и отправляем через send()
    await cl.Message(content="Привет! Я ваш ИИ-агент. Чем могу помочь?").send()

# @cl.on_message — вызывается, когда пользователь отправляет сообщение
@cl.on_message
async def main(message: cl.Message):
    """Вызывается, когда пользователь присылает сообщение"""
    
    # Получаем chat_id из user_session или из контекста сессии
    chat_id = cl.user_session.get("chat_id") or cl.context.session.thread_id
    
    # Сохраняем chat_id в user_session
    cl.user_session.set("chat_id", chat_id)
    
    # Создаем пустой контейнер для ответа агента в UI
    final_response = cl.Message(content="")
    
    # Отправляем сообщение на backend через WebSocket
    try:
        import asyncio  # Импортируем asyncio для асинхронных операций
        import websockets  # Импортируем websockets для WebSocket-соединения
        
        # Открываем WebSocket-соединение с бэкендом
        # Формируем URL: BACKEND_WS_URL + /chat_id
        # Например: ws://localhost:8001/ws/{chat_id}
        async with websockets.connect(f"{BACKEND_WS_URL}/{chat_id}") as ws:
            # Отправляем сообщение на backend
            # Сериализуем JSON с типом сообщения и контентом
            await ws.send(json.dumps({
                "type": "message",  # Тип сообщения — "message"
                "content": message.content  # Контент сообщения пользователя
            }))
            
            # Собираем ответ
            while True:  # Бесконечный цикл для ожидания ответа
                response = await ws.recv()  # Получаем ответ от backend
                data = json.loads(response)  # Парсим JSON-ответ
                
                # Если это thought — размышления агента
                if data["type"] == "thought":
                    # Показываем размышления
                    # Создаём Step с name="размышления" и type="run"
                    async with cl.Step(name="размышления", type="run") as step:
                        # Устанавливаем output — содержимое размышлений
                        step.output = data["content"]
                
                # Если это tool_call — использование инструмента
                elif data["type"] == "tool_call":
                    # Показываем использование инструмента
                    # Создаём Step с name="{name}" и type="tool"
                    async with cl.Step(name=f"{data['name']}", type="tool") as step:
                        # Устанавливаем input — аргументы вызова
                        step.input = f"Аргументы: {data.get('args', '')}"
                
                # Если это tool_result — результат использования инструмента
                elif data["type"] == "tool_result":
                    # Показываем результат
                    # Создаём Step с name="результат {name}" и type="tool"
                    async with cl.Step(name=f"результат {data['name']}", type="tool") as step:
                        # Устанавливаем output — содержимое результата
                        step.output = data["content"]
                
                # Если это final — финальный ответ
                elif data["type"] == "final":
                    # Финальный ответ
                    # Устанавливаем content финального ответа
                    final_response.content = data["content"]
                    break  # Прерываем цикл, ответ получен
                
                # Если это error — ошибка
                elif data["type"] == "error":
                    # Отправляем ошибку пользователю
                    # Создаём ErrorMessage с content
                    await cl.ErrorMessage(content=data["content"]).send()
                    break  # Прерываем цикл, ошибка
            
    except Exception as e:
        # Отправляем ошибку пользователю
        await cl.ErrorMessage(content=f"Ошибка подключения к бэкенду: {str(e)}").send()

    # Отправляем финальный ответ пользователю
    if final_response.content:
        await final_response.send()