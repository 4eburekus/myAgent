import os
import math
import requests
from pydantic_ai import RunContext
from config import agent, AssistantDeps

@agent.tool
def calculate(ctx: RunContext[AssistantDeps], expression: str) -> str:
    """Универсальный калькулятор для базовых математических операций. 
    Поддерживает только базовые действия (+, -, *, /), возведение в степень (**)
    и только функции модуля math.
    Примеры: '2**10', 'math.sqrt(16)', '(15 + 7) * 3'."""
    try:
        allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
        allowed_names['math'] = math
        result = eval(expression, {"__builtins__": None}, allowed_names)
        if isinstance(result, (int, float)):
            # нужно ли округление
            if isinstance(result, float):
                # округляем до 4 знаков после точки
                result = round(result, 4)
            return f"Результат вычисления {expression}: {result}"
        return f"Результат: {result}"
    except Exception as e:
        return f"Ошибка в расчете: {str(e)}. Проверьте корректность синтаксиса."

@agent.tool
def agent_notes(ctx: RunContext[AssistantDeps], action: str, text: str = "") -> str:
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
    if not city or not city.strip():
        return "Ошибка: Название города не предоставлено. Пожалуйста, укажите название города."
    city = city.strip()
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


