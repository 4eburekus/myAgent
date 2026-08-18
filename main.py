import os
import asyncio
import requests
from typing import List, Optional
from dataclasses import dataclass, field
from pydantic_ai import Agent, RunContext

# Указываем базовый URL LLM сервера
os.environ["OPENAI_BASE_URL"] = "http://10.45.0.75:8000/v1"

# Состояние и Зависимости
@dataclass
class AssistantDeps:
    """Это 'рюкзак' агента. Всё, что хранится здесь, доступно инструментам."""
    # Список заметок. field(default_factory=list) создает пустой список для каждого нового объекта.
    notes: List[str] = field(default_factory=list)

agent = Agent(
    model='openai:RedHatAi/Qwen3.6-35B-A3B-NVFP4',
    # Передаем класс зависимостей, чтобы Pydantic проверил типы
    deps_type=AssistantDeps,
    system_prompt=(
        "Ты — консольный ассистент. Правила:\n"
        "1. Используй инструмент 'calculate' для всех вычислений.\n"
        "2. Сохраняй результаты в 'manage_notes'.\n"
        "3. Перед вызовом инструмента кратко опиши, что ты собираешься сделать и почему.\n"
        "4. Стиль: краткий и четкий."
    ),
    retries=2
)

@agent.tool
def calculate(ctx: RunContext[AssistantDeps], expression: str) -> str:
    """Математический калькулятор. Принимает строку (например: '2 + 2 * 2')."""
    try:
        result = eval(expression, {"__builtins__": None}, {}) # eval исполняет строку как код Python
        return f"Результат вычисления {expression}: {result}"
    except Exception as e:
        return f"Ошибка в расчете: {e}"

@agent.tool
def manage_notes(ctx: RunContext[AssistantDeps], action: str, text: str = "") -> str:
    """Работа с заметками. 
    action: 'add' (чтобы сохранить текст) или 'list' (чтобы прочитать все)."""
    # ctx.deps — это доступ к объекту состояний
    if action == "add":
        ctx.deps.notes.append(text)
        return "Заметка сохранена."
    elif action == "list":
        if not ctx.deps.notes:
            return "Список заметок пуст."
        return f"Твои текущие заметки: {ctx.deps.notes}"
    return "Ошибка: выбери 'add' или 'list'."

@agent.tool
def search_in_file(ctx: RunContext[AssistantDeps], filename: str, pattern: str) -> str:
    """Ищет строки в файле, содержащие текст 'pattern'. 
    Аргументы: имя файла и текст для поиска"""
    if not os.path.exists(filename):
        return f"Файл {filename} не найден."
    with open(filename, 'r', encoding='utf-8') as f:
        found = [line.strip() for line in f if pattern.lower() in line.lower()]
    return f"Найдено {len(found)} строк: {found}"

@agent.tool
def get_weather(ctx: RunContext[AssistantDeps], city: str) -> str:
    """Получает текущую температуру в заданном городе.
    Аргумент 'city': название города (например, 'Москва' или 'Tokyo')."""
    try:
        # получаем координаты города
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=ru&format=json"
        geo_data = requests.get(geo_url, timeout=10).json()
        if not geo_data.get('results'):
            return f"Город '{city}' не найден."
        res = geo_data['results'][0]
        lat, lon, city_name = res['latitude'], res['longitude'], res['name']
        # получаем текущую температуру
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        weather_data = requests.get(weather_url, timeout=10).json()
        temp = weather_data['current_weather']['temperature']
        return f"Сейчас в городе {city_name}: {temp}°C"
    except Exception as e:
        return f"Ошибка при получении погоды: {e}"

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

        # message_history=history позволяет агенту помнить предыдущие реплики
        result = await agent.run(user_input, deps=deps, message_history=history)
        
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