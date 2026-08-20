# frontend/app.py — Chainlit UI с WebSocket-подключением к бэкенду
import sys
from pathlib import Path
import os
import json

sys.path.append(str(Path(__file__).resolve().parent.parent / "backend"))

import chainlit as cl
from config import agent, AssistantDeps
import tools  # noqa: register tools

# Backend WebSocket URL
BACKEND_WS_URL = os.getenv("BACKEND_WS_URL", "ws://localhost:8001/ws")


@cl.on_chat_start
async def start():
    """Вызывается при старте чата"""
    session_id = cl.user_session.get("session_id", "default")
    cl.user_session.set("chat_id", session_id)
    cl.user_session.set("streaming", False)
    cl.user_session.set("agent", None)

    await cl.Message(content="Привет! Я ваш ИИ-ассистент. Чем могу помочь?").send()


@cl.on_message
async def main(message: cl.Message):
    """Вызывается, когда пользователь присылает сообщение"""

    session_id = cl.user_session.get("session_id", "default")
    chat_id = cl.user_session.get("chat_id", session_id)

    # Создаем пустой контейнер для ответа агента в UI
    final_response = cl.Message(content="")

    # Отправляем сообщение на backend через WebSocket
    try:
        import asyncio
        import websockets

        async with websockets.connect(f"{BACKEND_WS_URL}/{chat_id}") as ws:
            # Отправляем сообщение
            await ws.send(json.dumps({
                "type": "message",
                "content": message.content
            }))

            # Собираем ответ
            while True:
                response = await ws.recv()
                data = json.loads(response)

                if data["type"] == "thought":
                    # Показываем размышления
                    async with cl.Step(name="Размышления", type="run") as step:
                        step.output = data["content"]

                elif data["type"] == "tool_call":
                    # Показываем использование инструмента
                    async with cl.Step(name=f"Инструмент: {data['name']}", type="tool") as step:
                        step.input = f"Аргументы: {data.get('args', '')}"

                elif data["type"] == "tool_result":
                    # Показываем результат
                    async with cl.Step(name=f"Результат: {data['name']}", type="tool") as step:
                        step.output = data["content"]

                elif data["type"] == "final":
                    # Финальный ответ
                    final_response.content = data["content"]
                    break

                elif data["type"] == "error":
                    await cl.ErrorMessage(content=data["content"]).send()
                    break

    except Exception as e:
        await cl.ErrorMessage(content=f"Ошибка подключения к бэкенду: {str(e)}").send()

    # Отправляем финальный ответ пользователю
    if final_response.content:
        await final_response.send()
