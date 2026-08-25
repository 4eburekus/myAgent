"""Модуль для заполнения полей в .docx шаблонах данными из файла-источника.

Логика:
1. Детекция «полей» (пропусков) в абзацах тела документа (НЕ в таблицах).
   Виды полей: последовательности подчёркиваний (______), подчёркнутый текст
   (underline=True), подчёркнутые пробелы.
2. Извлечение смыслового контекста каждого поля:
   - если в абзаце есть текст до поля — это контекст;
   - если поле первое в абзаце — контекст из предыдущего непустого абзаца;
   - если это первое поле в документе — «начало документа».
3. Чтение файла-источника (.docx/.doc/.txt) в текст.
4. Семантическое сопоставление полей с данными через LLM (agent_matcher).
5. Заполнение полей с сохранением форматирования run'ов.
6. Сохранение копии <шаблон>_filled.docx.
"""
import os
import re
import json

from docx import Document
from docx.oxml.ns import qn


# ---------------------------------------------------------------
# 1. Детекция полей
# ---------------------------------------------------------------

# Регулярка для последовательностей подчёркиваний: ____, ___, __ __ и т.п.
UNDERSCORE_RE = re.compile(r'_{2,}')

# Виды полей
KIND_UNDERSCORE = "underscore"   # ______ (последовательность подчёркиваний)
KIND_UNDERLINE = "underline"     # подчёркнутый текст/пробелы (w:u)
KIND_SPACES = "spaces"           # подчёркнутые пробелы


def _in_table(paragraph) -> bool:
    """Проверяет, находится ли абзац внутри таблицы (w:tc — ячейка таблицы)."""
    el = paragraph._element
    while el is not None:
        if el.tag == qn('w:tc'):
            return True
        el = el.getparent()
    return False


def _iter_paragraphs_not_in_tables(doc):
    """Возвращает абзацы документа, не находящиеся в таблицах."""
    for p in doc.paragraphs:
        if not _in_table(p):
            yield p


def _runs_contain_underscore(run) -> bool:
    return bool(UNDERSCORE_RE.search(run.text))


def _run_is_underlined(run) -> bool:
    """Подчёркнут ли run (w:u не None)."""
    rpr = run._element.rPr
    if rpr is None:
        return False
    u = rpr.find(qn('w:u'))
    return u is not None and u.get(qn('w:val')) not in (None, 'none')


def _run_is_underlined_spaces(run) -> bool:
    """Подчёркнутый run, содержащий только пробелы (пустое поле)."""
    return _run_is_underlined(run) and run.text.strip() == '' and len(run.text) > 0


def detect_fields(doc):
    """Ищет поля в абзацах документа (вне таблиц).

    Возвращает список словарей:
    {
        'paragraph_idx': int,      # индекс абзаца в doc.paragraphs
        'run_idx': int,            # индекс run в абзаце
        'kind': str,               # KIND_*
        'field_text': str,         # исходный текст поля
        'label': str,              # смысловой контекст (текст до поля)
    }
    """
    fields = []
    # Предварительно соберём все абзацы тела (не в таблицах) с их текстом,
    # чтобы вычислять предыдущий непустой абзац для контекста.
    body_paragraphs = [p for p in doc.paragraphs if not _in_table(p)]

    for pi, para in enumerate(body_paragraphs):
        # Контекст по умолчанию — текст абзаца до поля (считаем далее посимвольно)
        prefix_builder = ""
        for ri, run in enumerate(para.runs):
            run_text = run.text or ""

            # --- Вид 1: последовательность подчёркиваний в тексте run'а ---
            if UNDERSCORE_RE.search(run_text):
                # Контекст = всё, что накопилось в абзаце до этого run'а
                label = prefix_builder.strip()
                if not label:
                    label = _find_prev_paragraph_context(body_paragraphs, pi)
                fields.append({
                    'paragraph_idx': pi,
                    'run_idx': ri,
                    'kind': KIND_UNDERSCORE,
                    'field_text': run_text,
                    'label': label or "начало документа",
                })
                prefix_builder += run_text
                continue

            # --- Вид 2: подчёркнутый текст (не только пробелы) ---
            if _run_is_underlined(run) and run_text.strip() != '':
                label = prefix_builder.strip()
                if not label:
                    label = _find_prev_paragraph_context(body_paragraphs, pi)
                fields.append({
                    'paragraph_idx': pi,
                    'run_idx': ri,
                    'kind': KIND_UNDERLINE,
                    'field_text': run_text,
                    'label': label or "начало документа",
                })
                prefix_builder += run_text
                continue

            # --- Вид 3: подчёркнутые пробелы (пустое поле) ---
            if _run_is_underlined_spaces(run):
                label = prefix_builder.strip()
                if not label:
                    label = _find_prev_paragraph_context(body_paragraphs, pi)
                fields.append({
                    'paragraph_idx': pi,
                    'run_idx': ri,
                    'kind': KIND_SPACES,
                    'field_text': run_text,
                    'label': label or "начало документа",
                })
                prefix_builder += run_text
                continue

            # Обычный текст — накапливаем контекст
            prefix_builder += run_text

    return fields


def _find_prev_paragraph_context(body_paragraphs, pi):
    """Ищет текст предыдущего непустого абзаца как контекст поля."""
    for prev in range(pi - 1, -1, -1):
        txt = body_paragraphs[prev].text.strip()
        if txt:
            # Убираем завершающее двоеточие у подписи
            return txt.rstrip(':：').strip()
    return ""


# ---------------------------------------------------------------
# 2. Чтение файла-источника
# ---------------------------------------------------------------

def read_source_file(filepath: str) -> str:
    """Читает файл-источник (.docx/.doc/.txt) и возвращает текст."""
    ext = os.path.splitext(filepath)[1].lower()
    if ext == '.docx':
        doc = Document(filepath)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    elif ext == '.doc':
        import docx2txt
        return docx2txt.process(filepath).strip()
    else:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()


# ---------------------------------------------------------------
# 3. Заполнение полей
# ---------------------------------------------------------------

def fill_fields_in_doc(doc, fields, values: dict) -> int:
    """Заполняет найденные поля значениями. values: {номер_поля: значение}.

    Возвращает количество заполненных полей.
    """
    filled = 0
    body_paragraphs = [p for p in doc.paragraphs if not _in_table(p)]

    for i, field in enumerate(fields, start=1):
        value = (values.get(str(i)) or values.get(i) or "").strip()
        if not value:
            continue  # значение не найдено — поле остаётся

        try:
            para = body_paragraphs[field['paragraph_idx']]
            run = para.runs[field['run_idx']]
        except (IndexError, KeyError):
            continue

        kind = field['kind']
        run_text = run.text or ""

        if kind == KIND_UNDERSCORE:
            # Заменяем последовательность подчёркиваний на значение
            new_text = UNDERSCORE_RE.sub(value, run_text, count=1)
            run.text = new_text
        elif kind == KIND_UNDERLINE:
            # Меняем текст подчёркнутого run'а на значение (подчёркивание сохраняется)
            run.text = value
        elif kind == KIND_SPACES:
            # Заменяем пробелы на значение (подчёркивание сохраняется)
            run.text = value

        filled += 1

    return filled


# ---------------------------------------------------------------
# 4. Семантическое сопоставление через LLM
# ---------------------------------------------------------------

async def match_values_with_llm(fields, source_text: str) -> dict:
    """Отправляет поля и данные в agent_matcher, получает JSON {номер: значение}.

    Возвращает словарь {номер_поля (str): значение}.
    """
    from config import agent_matcher

    fields_desc = "\n".join(
        f"{i}. {f['label']}" for i, f in enumerate(fields, start=1)
    )

    prompt = (
        "Поля документа-шаблона (номер и смысловой контекст):\n"
        f"{fields_desc}\n\n"
        "Содержимое файла с данными:\n"
        f"{source_text[:12000]}\n\n"
        "Сопоставь каждое поле с подходящим значением из файла и верни "
        "строго JSON вида {\"1\": \"значение\", \"2\": \"значение\", ...}. "
        "Для ненайденных — пустая строка. Никакого текста кроме JSON."
    )

    try:
        result = await agent_matcher.run(prompt)
        raw = result.output.strip()
        # Обрезаем возможные ```json ... ``` обёртки
        if raw.startswith("```"):
            raw = re.sub(r'^```(?:json)?\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw)
        values = json.loads(raw)
        if not isinstance(values, dict):
            return {}
        return {str(k): str(v) for k, v in values.items()}
    except Exception:
        return {}


# ---------------------------------------------------------------
# 5. Главная функция
# ---------------------------------------------------------------

async def fill_docx_fields(template_path: str, source_path: str) -> str:
    """Заполняет поля шаблона данными из файла-источника.

    Возвращает текстовый отчёт для агента.
    """
    if not os.path.exists(template_path):
        return f"Ошибка: шаблон '{template_path}' не найден."
    if not os.path.exists(source_path):
        return f"Ошибка: файл-источник '{source_path}' не найден."

    try:
        doc = Document(template_path)
    except Exception as e:
        return f"Ошибка при открытии шаблона: {e}"

    # 1. Детекция полей
    fields = detect_fields(doc)
    if not fields:
        return "В документе не найдено полей для заполнения."

    # 2. Чтение источника
    try:
        source_text = read_source_file(source_path)
    except Exception as e:
        return f"Ошибка при чтении файла-источника: {e}"

    # 3. Семантическое сопоставление
    values = await match_values_with_llm(fields, source_text)

    # 4. Заполнение
    filled = fill_fields_in_doc(doc, fields, values)

    # 5. Сохранение копии
    base, ext = os.path.splitext(template_path)
    out_path = f"{base}_filled{ext}"
    try:
        doc.save(out_path)
    except Exception as e:
        return f"Ошибка при сохранении результата: {e}"

    # Отчёт
    lines = [f"Найдено полей: {len(fields)}, заполнено: {filled}"]
    for i, f in enumerate(fields, start=1):
        val = (values.get(str(i)) or values.get(i) or "").strip()
        status = "OK" if val else "—"
        lines.append(f"- {f['label']}: {val or '(не заполнено)'} [{status}]")
    lines.append(f"Сохранено: {out_path}")
    return "\n".join(lines)
