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
def create_docx(ctx: RunContext[AssistantDeps], filename: str, title: str, paragraphs: list) -> str:
    """Создаёт новый .docx файл с поддержкой форматирования.
    Аргументы:
    - filename: имя файла с расширением .docx
    - title: заголовок документа (строка)
    - paragraphs: список словарей с параметрами абзацев. Каждый словарь может содержать:
        * 'text' (str) — текст абзаца (обязательно)
        * 'style' (str) — стиль: 'heading' для заголовка, 'normal' для обычного текста
        * 'bold' (bool) — жирный текст (по умолчанию False)
        * 'italic' (bool) — курсив (по умолчанию False)
        * 'level' (int) — уровень заголовка 1-9 (по умолчанию 1)
        * 'alignment' (str) — 'left', 'center', 'right', 'justify'
        * 'font_size' (int) — размер шрифта в пунктах (по умолчанию 12 для normal, 14-26 для heading)
        * 'font_name' (str) — имя шрифта (по умолчанию 'Calibri')
        * 'space_before' (int) — отступ перед абзацем в пунктах (по умолчанию 0)
        * 'space_after' (int) — отступ после абзаца в пунктах (по умолчанию 6)
        * 'line_spacing' (float) — междустрочный интервал (по умолчанию 1.15)
    
    Пример:
    [{
        'text': 'Введение',
        'style': 'heading',
        'bold': True,
        'level': 1,
        'font_size': 22,
        'space_after': 12,
    }, {
        'text': 'Основной текст абзаца.',
        'style': 'normal',
        'bold': False,
        'italic': False,
        'font_size': 12,
        'space_after': 6,
    }]"""
    import os
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt, RGBColor, Cm
    
    # Рабочая директория
    workspace = os.getenv("AGENT_WORKSPACE", "/app/workspace")
    filepath = os.path.join(workspace, filename)
    
    # Проверяем, что имя файла заканчивается на .docx
    if not filename.lower().endswith('.docx'):
        return "Ошибка: имя файла должно заканчиваться на .docx"
    
    # Проверяем, что paragraphs — это список словарей
    if not isinstance(paragraphs, list):
        return "Ошибка: аргумент paragraphs должен быть списком"
    
    # Определяем размер шрифта по умолчанию
    DEFAULT_FONT_SIZE = 12
    DEFAULT_FONT_NAME = 'Calibri'
    
    try:
        # Создаём документ
        doc = Document()
        
        # Устанавливаем шрифт по умолчанию для всего документа
        default_style = doc.styles['Normal']
        default_font = default_style.font
        default_font.name = DEFAULT_FONT_NAME
        default_font.size = Pt(DEFAULT_FONT_SIZE)
        default_style.paragraph_format.space_after = Pt(6)
        default_style.paragraph_format.space_before = Pt(0)
        default_style.paragraph_format.line_spacing = Pt(DEFAULT_FONT_SIZE * 1.15)
        
        # Добавляем заголовок документа (как заголовок уровня 1)
        title_para = doc.add_heading(title, level=1)
        title_run = title_para.runs[0]
        title_run.font.bold = True
        title_run.font.size = Pt(24)
        title_run.font.color.rgb = RGBColor(0, 51, 102)  # Тёмно-синий цвет
        
        # Добавляем абзацы
        for para in paragraphs:
            if not isinstance(para, dict):
                return f"Ошибка: каждый абзац должен быть словарём. Получено: {type(para).__name__}"
            
            text = para.get('text', '')
            if not text:
                continue
            
            # Определяем стиль
            style = para.get('style', 'normal')
            bold = para.get('bold', False)
            italic = para.get('italic', False)
            level = para.get('level', 1)
            alignment = para.get('alignment', 'left')
            font_size = para.get('font_size', DEFAULT_FONT_SIZE)
            font_name = para.get('font_name', DEFAULT_FONT_NAME)
            space_before = para.get('space_before', 0)
            space_after = para.get('space_after', 0)
            line_spacing = para.get('line_spacing', 1.15)
            
            # Создаём абзац
            p = doc.add_paragraph()
            
            # Добавляем текст
            run = p.add_run(text)
            
            # Устанавливаем шрифт
            run.font.name = font_name
            run.font.size = Pt(font_size)
            
            # Устанавливаем форматирование
            run.font.bold = bold
            run.font.italic = italic
            run.font.color.rgb = RGBColor(0, 0, 0)  # Чёрный цвет
            
            # Устанавливаем выравнивание
            align_map = {
                'left': WD_ALIGN_PARAGRAPH.LEFT,
                'center': WD_ALIGN_PARAGRAPH.CENTER,
                'right': WD_ALIGN_PARAGRAPH.RIGHT,
                'justify': WD_ALIGN_PARAGRAPH.JUSTIFY,
            }
            p.paragraph_format.alignment = align_map.get(alignment, WD_ALIGN_PARAGRAPH.LEFT)
            
            # Устанавливаем отступы
            p.paragraph_format.space_before = Pt(space_before)
            p.paragraph_format.space_after = Pt(space_after)
            p.paragraph_format.line_spacing = Pt(font_size * line_spacing)
            
            # Если заголовок — используем заголовочный стиль
            if style == 'heading':
                p.clear()
                heading_para = doc.add_heading(text, level=min(level, 9))
                heading_run = heading_para.runs[0]
                heading_run.font.color.rgb = RGBColor(0, 51, 102)
                # Обновляем форматирование заголовка
                heading_run.font.bold = bold or True
                heading_run.font.italic = italic
                heading_run.font.size = Pt(font_size)
        
        # Сохраняем файл
        doc.save(filepath)
        return f"Файл '{filename}' успешно создан с {len(paragraphs) + 1} абзацами (включая заголовок) в {workspace}"
    
    except Exception as e:
        return f"Ошибка при создании файла: {str(e)}"


@agent.tool
def append_to_docx(ctx: RunContext[AssistantDeps], filename: str, paragraphs: list) -> str:
    """Добавляет новые абзацы в существующий .docx файл.
    Аргументы:
    - filename: имя существующего файла .docx
    - paragraphs: список словарей с параметрами абзацев. Каждый словарь может содержать:
        * 'text' (str) — текст абзаца (обязательно)
        * 'style' (str) — стиль: 'heading' для заголовка, 'normal' для обычного текста
        * 'bold' (bool) — жирный текст (по умолчанию False)
        * 'italic' (bool) — курсив (по умолчанию False)
        * 'level' (int) — уровень заголовка 1-9 (по умолчанию 1)
        * 'alignment' (str) — 'left', 'center', 'right', 'justify'
        * 'font_size' (int) — размер шрифта в пунктах (по умолчанию 12 для normal, 14-26 для heading)
        * 'font_name' (str) — имя шрифта (по умолчанию 'Calibri')
        * 'space_before' (int) — отступ перед абзацем в пунктах (по умолчанию 0)
        * 'space_after' (int) — отступ после абзаца в пунктах (по умолчанию 6)
        * 'line_spacing' (float) — междустрочный интервал (по умолчанию 1.15)
    
    Пример:
    [{
        'text': 'Введение',
        'style': 'heading',
        'bold': True,
        'level': 1,
        'font_size': 22,
        'space_after': 12,
    }, {
        'text': 'Основной текст абзаца.',
        'style': 'normal',
        'bold': False,
        'italic': False,
        'font_size': 12,
        'space_after': 6,
    }]
    
    Новые абзацы добавляются в конец документа. Существующие абзацы не удаляются и не изменяются.
    Это позволяет наращивать документ постепенно."""
    import os
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt, RGBColor
    
    workspace = os.getenv("AGENT_WORKSPACE", "/app/workspace")
    filepath = os.path.join(workspace, filename)
    
    # Проверяем, что файл существует
    if not os.path.exists(filepath):
        return f"Файл '{filename}' не найден."
    
    if not isinstance(paragraphs, list):
        return "Ошибка: аргумент paragraphs должен быть списком"
    
    DEFAULT_FONT_SIZE = 12
    DEFAULT_FONT_NAME = 'Calibri'
    
    try:
        # Открываем существующий документ
        doc = Document(filepath)
        
        # Получаем количество абзацев ДО добавления
        old_para_count = len(doc.paragraphs)
        
        # Добавляем каждый новый абзац
        for para in paragraphs:
            if not isinstance(para, dict):
                return f"Ошибка: каждый абзац должен быть словарём"
            
            text = para.get('text', '')
            if not text:
                continue
            
            style = para.get('style', 'normal')
            bold = para.get('bold', False)
            italic = para.get('italic', False)
            level = para.get('level', 1)
            alignment = para.get('alignment', 'left')
            font_size = para.get('font_size', DEFAULT_FONT_SIZE)
            font_name = para.get('font_name', DEFAULT_FONT_NAME)
            space_before = para.get('space_before', 0)
            space_after = para.get('space_after', 0)
            line_spacing = para.get('line_spacing', 1.15)
            
            if style == 'heading':
                # Создаём заголовочный абзац
                heading = doc.add_heading(text, level=min(level, 9))
                run = heading.runs[0]
                run.font.color.rgb = RGBColor(0, 51, 102)
                run.font.bold = True
                run.font.size = Pt(font_size)
            else:
                # Обычный абзац
                p = doc.add_paragraph()
                run = p.add_run(text)
                run.font.name = font_name
                run.font.size = Pt(font_size)
                run.font.bold = bold
                run.font.italic = italic
                run.font.color.rgb = RGBColor(0, 0, 0)
                
                align_map = {
                    'left': WD_ALIGN_PARAGRAPH.LEFT,
                    'center': WD_ALIGN_PARAGRAPH.CENTER,
                    'right': WD_ALIGN_PARAGRAPH.RIGHT,
                    'justify': WD_ALIGN_PARAGRAPH.JUSTIFY,
                }
                p.paragraph_format.alignment = align_map.get(alignment, WD_ALIGN_PARAGRAPH.LEFT)
                p.paragraph_format.space_before = Pt(space_before)
                p.paragraph_format.space_after = Pt(space_after)
                p.paragraph_format.line_spacing = Pt(font_size * line_spacing)
        
        # Сохраняем файл
        doc.save(filepath)
        added_count = len(doc.paragraphs) - old_para_count
        return f"Успешно добавлено {added_count} абзацев в '{filename}'. Всего абзацев: {len(doc.paragraphs)}."
    
    except Exception as e:
        return f"Ошибка при добавлении: {str(e)}"


@agent.tool
def read_docx(ctx: RunContext[AssistantDeps], filename: str) -> str:
    """Читает содержимое .docx файла из папки /app/workspace.
    Аргумент filename: имя файла (с расширением .docx)
    Возвращает текстовое содержимое файла."""
    import os
    from docx import Document
    
    # Рабочая директория
    workspace = os.getenv("AGENT_WORKSPACE", "/app/workspace")
    filepath = os.path.join(workspace, filename)
    
    # Проверяем, что файл существует
    if not os.path.exists(filepath):
        return f"Файл '{filename}' не найден."
    
    try:
        # Открываем документ
        doc = Document(filepath)
        
        # Собираем все абзацы
        text_parts = []
        for para in doc.paragraphs:
            if para.text.strip():  # пропускаем пустые абзацы
                text_parts.append(para.text)
        
        return "\n\n".join(text_parts)
    
    except Exception as e:
        return f"Ошибка при чтении файла: {str(e)}"




