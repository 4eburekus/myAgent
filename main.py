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
        "3. Стиль: краткий и четкий."
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

# # Трассировка и запуск для тестовых сценариев
# async def run_scenario(prompt: str, deps: AssistantDeps):
#     print(f"\n>>> ЗАПРОС: {prompt}")
#     result = await agent.run(prompt, deps=deps)
#     print("\n[ЛОГ ВЫЗОВОВ]:")
#     for msg in result.new_messages():
#         # В Pydantic AI сообщения состоят из частей (parts)
#         if hasattr(msg, 'parts'):
#             for part in msg.parts:
#                 # Проверяем, является ли это вызовом инструмента (есть имя и аргументы)
#                 if hasattr(part, 'tool_name') and hasattr(part, 'args'):
#                     print(f"🛠  Агент вызвал: {part.tool_name}({part.args})")
#                 # Проверяем, является ли это ответом инструмента (есть имя и контент)
#                 elif hasattr(part, 'tool_name') and hasattr(part, 'content'):
#                     print(f"📥 Инструмент [{part.tool_name}] вернул: {part.content}")
#     if hasattr(result, 'output'):
#         final_text = result.output
#     elif hasattr(result, 'data'):
#         final_text = result.data
#     else:
#         final_text = str(result)
#     print(f"\n[ОТВЕТ]:{final_text}\n")
 
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
        # Трассировка вызовов инструментов
        for msg in result.new_messages():
            if hasattr(msg, 'parts'):
                for part in msg.parts:
                    # Проверяем, является ли это вызовом инструмента (есть имя и аргументы)
                    if hasattr(part, 'tool_name') and hasattr(part, 'args'):
                        print(f"🛠  Агент вызвал: {part.tool_name}({part.args})")
                    # Проверяем, является ли это ответом инструмента (есть имя и контент)
                    elif hasattr(part, 'tool_name') and hasattr(part, 'content'):
                        print(f"📥 Инструмент [{part.tool_name}] вернул: {part.content}")
        # Обновляем историю сообщений (добавляем туда новый обмен репликами)
        history = result.all_messages()
        # Вывод финального ответа
        if hasattr(result, 'output'):
            final_text = result.output
        elif hasattr(result, 'data'):
            final_text = result.data
        else:
            final_text = str(result)
        print(f"ОТВЕТ:{final_text}\n")

async def main():
    with open("tasks.txt", "w", encoding="utf-8") as f:
        f.write("Дедлайн: завтра подготовить отчет\nКупить хлеб\nЕще один дедлайн в пятницу")
    # Инициализируем состояния и зависимости
    deps = AssistantDeps()
    # Демо-сценарии
    # await run_scenario("Найди в tasks.txt строки со словом “дедлайн” и посчитай их", deps)
    # await run_scenario("Какая погода в Екатеринбурге и в Москве? Сравни температуры", deps)
    # await run_scenario("Посчитай (15+7)×3 и запиши результат в заметку", deps)
    # await run_scenario("Поищи слово 'пароль' в файле secret.txt", deps) # Файла нет
    await interactive_chat()

if __name__ == "__main__":
    asyncio.run(main())