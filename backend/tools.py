import os
import math
import requests  # импортируем requests для HTTP-запросов к внешним API (погода)
from pydantic_ai import RunContext  # импортируем RunContext — контекст выполнения агента (доступ к deps, chat_id и т.д.)
from config import agent, AssistantDeps

@agent.tool
def calculate(ctx: RunContext[AssistantDeps], expression: str) -> str:
    """Универсальный калькулятор для базовых математических операций. 
    Поддерживает только базовые действия (+, -, *, /), возведение в степень (**)
    и только функции модуля math.
    Примеры: '2**10', 'math.sqrt(16)', '(15 + 7) * 3'."""
    try:
        # словарь разрешённых имён — извлекаем все атрибуты модуля math,
        # кроме тех, что начинаются с '__' (магические методы, чтобы избежать инъекций)
        allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
        # Добавляем сам модуль math в разрешённые (чтобы можно было использовать math.xxx)
        allowed_names['math'] = math
        # Выполняем выражение через eval с ограниченной областью видимости:
        # - __builtins__ = None — запрещаем встроенные функции (open, eval и т.д.)
        # - allowed_names — только функции из math
        result = eval(expression, {"__builtins__": None}, allowed_names)
        if isinstance(result, (int, float)):
            if isinstance(result, float):
                result = round(result, 4)
            return f"Результат вычисления {expression}: {result}"
        return f"Результат: {result}"
    except Exception as e:
        return f"Ошибка в расчете: {str(e)}. Проверьте корректность синтаксиса."


@agent.tool
def agent_notes(ctx: RunContext[AssistantDeps], action: str, text: str = "") -> str:
    """Работа с заметками. 
    action: 'add' (чтобы сохранить текст) или 'list' (чтобы прочитать все)."""
    from config import get_db
    # Получаем базу данных MongoDB
    db = get_db()
    # Находим документ чата по chat_id из контекста агента
    chat = db["chats"].find_one({"_id": ctx.deps.chat_id})
    if not chat:
        return "Ошибка: чат не найден."
    # Получаем список заметок из документа чата (или пустой список)
    notes = chat.get("notes", [])

    if action == "add":
        notes.append(text)
        db["chats"].update_one(
            {"_id": ctx.deps.chat_id},  # фильтр — ищем чат по _id
            {"$set": {"notes": notes}}   # операция: установить поле notes
        )
        return "Заметка сохранена."
    elif action == "list":
        if not notes:
            return "Список заметок пуст."
        return f"Твои текущие заметки: {notes}"
    return "Ошибка: выбери 'add' или 'list'."


@agent.tool
def run_console_command(ctx: RunContext[AssistantDeps], command: str) -> str:
    """Работает с консолью компьютера пользователя.
    Запускает безопасную Linux-команду в папке /app/workspace (внутри контейнера).
    Работает для просмотра/редактирования файлов, перемещения, копирования и 
    создания папок. Все файлы/папки строго внутри workspace.
    
    Ограничения:
    - 5 секунд на команду (timeout)
    - Вывод ограничен 10 KB (лимит на вывод)
    - Только разрешённые команды (whitelist: ls, cat, cp, mv, mkdir, echo, find, grep, wc, head, tail, pwd, whoami, date, uptime, chmod, chown, touch, ln, du, stat, file, readlink, basename, dirname)
    - Запрещено: rm, любые команды, выходящие за пределы workspace
    - Путь: должен начинаться с /app/workspace или быть относительным (без ..)
    """
    # Импортируем функцию безопасности из sandbox.py
    from sandbox import run_console_command
    result = run_console_command(command)
    return f"Результат выполнения команды: {result}"


@agent.tool
def set_chat_title(ctx: RunContext[AssistantDeps], title: str) -> str:
    """Сохраняет название чата. Вызови в начале разговора, когда понял тему диалога.
    Используй только если пользователь просит сменить название чата.
    Аргумент title: короткое название (3-6 слов), отражающее суть разговора."""
    from config import get_db
    db = get_db()
    chat = db["chats"].find_one({"_id": ctx.deps.chat_id})
    if not chat:
        return "Ошибка: чат не найден."
    # Получаем текущее название чата
    current = chat.get("name") or ""
    # Обрезаем название до 60 символов, убираем пробелы по краям
    title = title.strip()[:60]
    if not title:
        return "Ошибка: название не может быть пустым."
    # Обновляем название чата в Mongo
    db["chats"].update_one({"_id": ctx.deps.chat_id}, {"$set": {"name": title}})
    return "Название чата сохранено."


@agent.tool
def search_in_file(ctx: RunContext[AssistantDeps], filename: str, pattern: str) -> str:
    """Ищет строки в файле, содержащие текст 'pattern'. 
    Аргументы: имя файла и текст для поиска"""
    # Проверяем, существует ли файл
    if not os.path.exists(filename):
        return f"Файл {filename} не найден."
    with open(filename, 'r', encoding='utf-8') as f:
        # Ищем строки, содержащие pattern (case-insensitive)
        found = [line.strip() for line in f if pattern.lower() in line.lower()]
    return f"Найдено {len(found)} строк: {found}"


@agent.tool
def get_weather(ctx: RunContext[AssistantDeps], city: str) -> str:
    """Получает текущую температуру в заданном городе.
    Аргумент 'city': название города (например, 'Москва' или 'Tokyo')."""
    if not city or not city.strip():
        return "Ошибка: Название города не предоставлено. Пожалуйста, укажите название города."
    # Убираем лишние пробелы
    city = city.strip()
    try:
        # Получаем координаты города
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=ru&format=json"
        # Делаем HTTP GET запрос с таймаутом 10 секунд
        geo_data = requests.get(geo_url, timeout=10).json()
        if not geo_data.get('results'):
            return f"Город '{city}' не найден."
        res = geo_data['results'][0]
        lat, lon, city_name = res['latitude'], res['longitude'], res['name']
        # Получаем текущую погоду
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        # Делаем HTTP GET запрос
        weather_data = requests.get(weather_url, timeout=10).json()
        # Извлекаем температуру (там много показателей)
        temp = weather_data['current_weather']['temperature']
        return f"Сейчас в городе {city_name}: {temp}°C"
    except Exception as e:
        return f"Ошибка при получении погоды: {e}"