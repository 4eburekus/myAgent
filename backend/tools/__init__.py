"""Пакет инструментов агента.

Содержит все модули-инструменты:
- agent_tools.py  — сами инструменты (@agent.tool), ранее backend/tools.py
- sandbox.py      — безопасное выполнение консольных команд
- docx_fields.py  — заполнение полей в .docx шаблонах
- docx_styles.py  — общие стили для .docx (копия styles.py)
- excel_utils.py  — чтение/создание/редактирование Excel
- md_to_docx.py   — конвертация Markdown в .docx

Импорт пакета (`import tools`) регистрирует все инструменты в агенте:
agent_tools.py выполняется при импорте (декораторы @agent.tool).

Остальные подмодули (docx_fields, excel_utils, md_to_docx, sandbox)
импортируются ЛЕНИВО — внутри функций agent_tools.py. Это позволяет
импортировать пакет в frontend без тяжёлых зависимостей (python-docx,
openpyxl и т.п.), которые нужны только backend-контейнеру.
"""
from . import agent_tools
