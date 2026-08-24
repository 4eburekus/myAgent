# CLI-интерфейс для запуска агента в режиме реального времени
import asyncio
import os
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent / "backend"))

from config import agent, AssistantDeps

async def main():
    """Инициализирует и запускает агента в цикле запросов."""
    
    print("Агент готов, введите запрос (или 'quit' для выхода):")
    while True:
        message = input("You: ")
        if message.lower() == 'quit':
            break
        deps = AssistantDeps(notes=[], chat_id="")

        result = await agent.run(message, deps=deps)
        print(f"Agent: {result.output}")
        print()


if __name__ == "__main__": 
    asyncio.run(main())