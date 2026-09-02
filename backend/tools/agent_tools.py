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
    from .sandbox import run_console_command
    result = run_console_command(command)
    return f"Результат выполнения команды: {result}"


@agent.tool
def set_chat_title(ctx: RunContext[AssistantDeps], title: str) -> str:
    """Изменяет название чата.
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


@agent.tool
async def fill_docx_fields(ctx: RunContext[AssistantDeps], template: str, source_file: str) -> str:
    """Заполняет поля в .docx-шаблоне данными из файла-источника.
    
    Аргументы:
    - template: имя .docx-файла-шаблона в папке /app/workspace (например 'anketa.docx')
    - source_file: имя файла с данными (.docx, .doc или .txt) в /app/workspace (например 'dannye.txt')
    
    Что делает:
    1. Находит в шаблоне все «поля» (пропуски): последовательности подчёркиваний ____,
       подчёркнутый текст, подчёркнутые пробелы. Поля ВНУТРИ таблиц не заполняются.
    2. Для каждого поля определяет смысловой контекст (подпись перед ним, или текст
       предыдущего абзаца, или начало документа).
    3. Читает файл-источник и сопоставляет контекст полей с данными (по смыслу, через LLM:
       'Имя' может соответствовать 'ФИО' и т.п.).
    4. Вставляет значения в поля, сохраняя форматирование.
    5. Сохраняет результат как копию: <template>_filled.docx (исходник не меняется).
    
    Возвращает отчёт: сколько полей найдено и заполнено, что именно вставлено."""
    import os
    from .docx_fields import fill_docx_fields as _fill

    workspace = os.getenv("AGENT_WORKSPACE", "/app/workspace")

    # Защита от выхода за пределы workspace
    template_path = os.path.join(workspace, os.path.basename(template))
    source_path = os.path.join(workspace, os.path.basename(source_file))

    if not template.lower().endswith('.docx'):
        return "Ошибка: шаблон должен быть .docx файлом."

    return await _fill(template_path, source_path)


@agent.tool
def read_excel(ctx: RunContext[AssistantDeps], filename: str, sheet: str = "", max_rows: int = 100) -> str:
    """Читает содержимое Excel-файла (.xlsx или .xls) из папки /app/workspace.
    
    Аргументы:
    - filename: имя файла (например 'data.xlsx' или 'data.xls')
    - sheet: имя листа (если не указано — берётся первый лист)
    - max_rows: максимальное количество строк для вывода (по умолчанию 100)
    
    Возвращает содержимое в виде текстовой таблицы: лист, количество строк/колонок,
    заголовки и строки данных."""
    from .excel_utils import read_excel as _read
    return _read(filename, sheet, max_rows)


@agent.tool
def create_excel(ctx: RunContext[AssistantDeps], filename: str, headers: list, rows: list, sheet_name: str = "Лист1") -> str:
    """Создаёт новый Excel-файл (.xlsx) в папке /app/workspace.
    
    Аргументы:
    - filename: имя файла с расширением .xlsx (например 'data.xlsx')
    - headers: список названий колонок (например ['Имя', 'Возраст'])
    - rows: список строк; каждая строка — список значений (например [['Иван', 30], ['Пётр', 25]])
    - sheet_name: название листа (по умолчанию 'Лист1')
    
    Заголовки делаются жирными, ширина колонок подстраивается автоматически."""
    from .excel_utils import create_excel as _create
    return _create(filename, headers, rows, sheet_name)


@agent.tool
def edit_excel(ctx: RunContext[AssistantDeps], filename: str, action: str, sheet: str = "", **kwargs) -> str:
    """Редактирует существующий Excel-файл (.xlsx или .xls) в папке /app/workspace.
    
    Аргументы:
    - filename: имя файла
    - action: тип операции (см. ниже)
    - sheet: имя листа (если не указано — первый лист)
    
    Действия (action) и их параметры:
    - set_cell: cell='A1', value=<значение> — записать значение в ячейку
    - add_row: row=[значения...] — добавить строку в конец
    - add_column: header='Название', values=[значения...] — добавить колонку
    - update_row: row_idx=<номер строки, начиная с 1>, values=[значения...] — заменить строку
    - clear_cell: cell='B3' — очистить ячейку
    - rename_sheet: new_name='Новое имя' — переименовать лист
    
    При редактировании форматирование остальных ячеек сохраняется. Файлы .xls
    конвертируются в .xlsx (результат сохраняется рядом с тем же именем, но .xlsx)."""
    from .excel_utils import edit_excel as _edit
    return _edit(filename, action, sheet, **kwargs)


@agent.tool
def md_to_docx(ctx: RunContext[AssistantDeps], filename: str, out_filename: str = "") -> str:
    """Преобразует Markdown-отчёт в .docx с красивым форматированием.
    
    Аргументы:
    - filename: имя .md файла в папке /app/workspace (например 'отчет.md')
    - out_filename: имя результирующего .docx (по умолчанию <имя>.docx, перезаписывается)
    
    Поддерживаемые конструкции Markdown (соответствие стилям):
    - # / ## / ### — заголовки 1-3 уровней
    - обычные абзацы (разделены пустыми строками)
    - ``` код ``` — блоки кода с рамкой
    - ![](путь/к/картинке.jpg) — изображения с подписью 'Рис. N'
    - 1. / * / - — вложенные списки (большой/средний/малый)
    - таблицы вида:
        | Название таблицы
        ||Столбец1|Столбец2|Столбец3
        |-|-|-|----|
        |Строка1|Ячейка1|Ячейка2|Ячейка3
    
    Стили берутся из docx_styles.py (соответствие instruction.md)."""
    import os
    from .md_to_docx import md_to_docx as _convert

    workspace = os.getenv("AGENT_WORKSPACE", "/app/workspace")

    md_path = os.path.join(workspace, os.path.basename(filename))
    if not os.path.exists(md_path):
        return f"Ошибка: файл '{filename}' не найден."

    if not out_filename:
        base = os.path.splitext(os.path.basename(filename))[0]
        out_filename = base + ".docx"
    out_path = os.path.join(workspace, os.path.basename(out_filename))

    return _convert(md_path, out_path)


@agent.tool
def add_title_to_docx(ctx: RunContext[AssistantDeps], filename: str,
                      discipline: str, workName: str, workTheme: str,
                      positionInspector: str, inspector: str,
                      workers: list, workersGroup: str = "23-ИСбо-4б") -> str:
    """Добавляет титульную страницу в начало существующего .docx файла.

    Аргументы:
    - filename: имя .docx файла в папке /app/workspace (перезаписывается)
    - discipline: название дисциплины
    - workName: название работы (например 'Лабораторная работа №6')
    - workTheme: тема работы
    - positionInspector: должность проверяющего
    - inspector: ФИО проверяющего
    - workers: список выполнивших (например ['Кузнецов Павел Михайлович', 'Пылова Виктория Дмитриевна'])
    - workersGroup: название группы (по умолчанию '23-ИСбо-4б')

    Титульник вставляется в НАЧАЛО документа. Существующее содержимое и его
    форматирование не изменяются — документ открывается, титульник добавляется,
    файл перезаписывается."""
    import os
    from docx import Document
    from .docx_styles import add_styles, add_title_page

    workspace = os.getenv("AGENT_WORKSPACE", "/app/workspace")
    filepath = os.path.join(workspace, os.path.basename(filename))

    if not os.path.exists(filepath):
        return f"Ошибка: файл '{filename}' не найден."
    if not filename.lower().endswith('.docx'):
        return "Ошибка: файл должен быть .docx."

    try:
        doc = Document(filepath)
        # Добавляем недостающие стили (если документ создан не нами — titleText* отсутствуют)
        add_styles(doc)
        add_title_page(
            doc,
            discipline=discipline,
            workName=workName,
            workTheme=workTheme,
            positionInspector=positionInspector,
            inspector=inspector,
            workers=workers,
            workersGroup=workersGroup,
            insert_at_beginning=True,
        )
        doc.save(filepath)
        return f"Титульный лист добавлен в начало '{filename}'."
    except Exception as e:
        return f"Ошибка при добавлении титульного листа: {e}"




