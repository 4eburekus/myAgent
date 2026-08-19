import asyncio
from typing import List
from pydantic_ai import messages

from config import agent, AssistantDeps
import tools

async def interactive_chat():
    deps = AssistantDeps()
    # Список для хранения истории переписки
    history: List[messages.ModelMessage] = []
    print("(Введите 'выход' или 'exit' для завершения)\n")

    while True:
        # Получаем ввод пользователя
        user_input = input("ВЫ: ")
        if user_input.lower() in ['выход', 'exit', 'пока', 'до свидания', '', '']:
            print("До свидания!")
            break

        agent_task = asyncio.create_task(agent.run(user_input, deps=deps, message_history=history))
        done, pending = await asyncio.wait({agent_task}, timeout=20.0)
        if agent_task in pending:
            agent_task.cancel() 
            print("\n⚠️  ВРЕМЯ ИСТЕКЛО: Агент не успел ответить за 2 минуты.")
            print("ОТВЕТ: Извините, я задумался слишком глубоко. Пожалуйста, попробуйте задать более простой вопрос или уточните детали.\n")
            continue
        result = agent_task.result()

        for msg in result.new_messages():
            if hasattr(msg, 'parts'):
                for part in msg.parts:

                    # Атрибут содержится в ModelResponse
                    if hasattr(part, 'provider_details') and part.provider_details:
                        raw_thoughts = part.provider_details.get('raw_content')
                        if raw_thoughts:
                            thoughts_text = "".join(raw_thoughts).strip()
                            if thoughts_text:
                                print("================================🧠БЛОК МЫСЛЕЙ🧠=====================================")
                                print(thoughts_text)
                                print("====================================================================================")
                    # Пара атрибутов содержится в ModelResponse
                    if hasattr(part, 'tool_name') and hasattr(part, 'args'):
                        print(f"🛠  ИСПОЛЬЗУЮ ИНСТРУМЕНТ: [{part.tool_name}] С ПАРАМЕТРАМИ: {part.args}")
                    # Пара атрибутов содержится в ModelRequest
                    if hasattr(part, 'tool_name') and hasattr(part, 'content'):
                        print(f"📥 РЕЗУЛЬТАТ [{part.tool_name}]: {part.content}")

        # Обновляем историю сообщений (добавляем туда новый обмен репликами)
        history = result.all_messages()
        print(f"ОТВЕТ:{result.output}\n")
        
async def main():
    with open("tasks.txt", "w", encoding="utf-8") as f:
        f.write("Дедлайн: завтра подготовить отчет\nКупить хлеб\nЕще один дедлайн в пятницу")
    # Инициализируем состояния и зависимости
    deps = AssistantDeps()
    await interactive_chat()

if __name__ == "__main__":
    asyncio.run(main())