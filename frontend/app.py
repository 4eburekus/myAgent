# frontend/app.py
import sys
from pathlib import Path

# Добавляем backend в путь импорта (независимо от папки запуска)
sys.path.append(str(Path(__file__).resolve().parent.parent / "backend"))

import chainlit as cl
from config import agent, AssistantDeps
import tools  # Регистрируем инструменты


@cl.on_chat_start
async def start():
    """Вызывается при старте чата"""
    # Инициализируем зависимости и историю для каждой сессии пользователя
    deps = AssistantDeps()
    history = []
    
    cl.user_session.set("deps", deps)
    cl.user_session.set("history", history)
    
    await cl.Message(content="Привет! Я ваш ИИ-ассистент. Чем могу помочь?").send()


@cl.on_message
async def main(message: cl.Message):
    """Вызывается, когда пользователь присылает сообщение"""
    
    # Достаем состояние сессии
    deps = cl.user_session.get("deps")
    history = cl.user_session.get("history")

    # Создаем пустой контейнер для ответа агента в UI
    final_response = cl.Message(content="")

    # Запускаем агента
    result = await agent.run(
        message.content, 
        deps=deps, 
        message_history=history
    )

    # Обрабатываем "ход мыслей" и инструменты для отображения в Chainlit
    for msg in result.new_messages():
        if hasattr(msg, 'parts'):
            for part in msg.parts:
                
                # 1. Отображаем МЫСЛИ (Thinking)
                if hasattr(part, 'provider_details') and part.provider_details:
                    raw_thoughts = part.provider_details.get('raw_content')
                    if raw_thoughts:
                        thought_text = "".join(raw_thoughts).strip()
                        # В Chainlit "мысли" красиво выглядят через Step
                        async with cl.Step(name="Размышления", type="run") as step:
                            step.output = thought_text

                # 2. Отображаем использование ИНСТРУМЕНТОВ
                if hasattr(part, 'tool_name'):
                    # Если это вызов (Request)
                    if hasattr(part, 'args'):
                        async with cl.Step(name=f"Инструмент: {part.tool_name}", type="tool") as step:
                            step.input = f"Аргументы: {part.args}"
                    
                    # Если это ответ инструмента (Return)
                    if hasattr(part, 'content'):
                        # Находим последний шаг инструмента и добавляем туда результат
                        async with cl.Step(name=f"Результат: {part.tool_name}") as step:
                            step.output = str(part.content)

    # Обновляем историю в сессии
    cl.user_session.set("history", result.all_messages())

    # Отправляем финальный ответ пользователю
    final_response.content = result.output
    await final_response.send()