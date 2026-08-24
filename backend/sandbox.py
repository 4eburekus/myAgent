import subprocess  # импортируем модуль subprocess для запуска внешних команд
import os  # для работы с переменными окружения
import re  # regex для работы с регулярными выражениями

WORKSPACE = os.getenv("AGENT_WORKSPACE")

# Максимальный размер вывода команды 10 КБ
MAX_OUTPUT_SIZE = 10240 # байт

ALLOWED = {
    "ls",        # list directory — список файлов и папок
    "cat",       # concatenate — чтение содержимого файла
    "cp",        # copy — копирование файлов
    "mv",        # move — перемещение/переименование файлов
    "mkdir",     # make directory — создание папки
    "echo",      # print string — запись строки в файл (echo "text" > file.txt)
    "find",      # search — поиск файлов и папок
    "grep",      # global regular expression print — поиск текста в файлах
    "wc",        # word count — подсчёт строк, слов, символов
    "head",      # показать начало файла (первые 10 строк)
    "tail",      # показать конец файла (последние 10 строк)
    "pwd",       # print working directory — показать текущую директорию
    "whoami",    # show current user — показать имя текущего пользователя
    "date",      # показать текущую дату и время
    "uptime",    # показать время работы системы
    "chmod",     # change mode — изменить права доступа к файлу
    "chown",     # change owner — изменить владельца файла
    "touch",     # create empty file — создать пустой файл
    "ln",        # link — создать символьную или жёсткую ссылку
    "du",        # disk usage — показать размер файлов и папок
    "stat",      # show file status — показать информацию о файле
    "file",      # determine file type — определить тип файла
    "readlink",  # display value of a symbolic link — показать содержимое ссылки
    "basename",  # strip directory and suffix from filenames — показать имя файла без пути
    "dirname",   # strip last component from filename — показать путь к файлу
}

def run_console_command(cmd: str) -> str:
    """Выполняет безопасную команду в директории workspace.
    Валидация:
    - команда должна быть в whitelist (ALLOWED)
    - запрещена команда 'rm' (безопасность)
    - запрещены пути с '..' (безопасность от выхода за пределы)
    - запрещены абсолютные пути вне workspace (безопасность от несанкционированного доступа)
    - таймаут 5 секунд (защита от бесконечных процессов)
    - лимит вывода 10 KB (защита от переполнения)
    """
    cmd = cmd.strip()
    if not cmd:
        return "Error: Empty command."
    # Разбиваем команду по пробелам на части
    cmd_parts = cmd.split()
    # Берём имя команды (ls, cat, echo и т.д.)
    command = cmd_parts[0]
    if command not in ALLOWED:
        return f"Error: Command '{command}' is not allowed. Allowed: {', '.join(sorted(ALLOWED))}"
    if command == "rm":
        return "Error: 'rm' is not allowed for safety."
    for part in cmd_parts[1:]:
        if ".." in part:
            return "Error: '..' in path is not allowed."
    # Если команда начинается с '/', но не начинается с WORKSPACE — это попытка выйти за пределы
    if cmd.startswith("/") and not cmd.startswith(WORKSPACE):
        return "Error: Absolute paths outside workspace are not allowed."
    # // — это нестандартный путь, который может быть попыткой обойти проверки
    if cmd.startswith("//") and not cmd.startswith(WORKSPACE):
        return "Error: Invalid path format."
    
    try:
        result = subprocess.run(
            cmd,
            shell=True, #сама команда (shell=True, чтобы работали pipe, >, >> и т.д.)
            cwd=WORKSPACE, #текущая директория
            timeout=5,
            capture_output=True, #перехватываем stdout и stderr (не показываем в терминал)
            text=True #читаем вывод как текст (не как байты)
        )
        # Собираем вывод команды
        output = result.stdout + result.stderr
        # Если команда вернула ошибку
        if result.returncode != 0:
            output = f"Command failed with exit code {result.returncode}.\n{output}"
        if len(output) > MAX_OUTPUT_SIZE:
            output = output[:MAX_OUTPUT_SIZE] + "\n[Output truncated due to size limit (10KB)]"
        
        if not output:
            output = "Command completed successfully (no output)."
        return output
    
    except subprocess.TimeoutExpired:
        return "Error: Command execution timed out (5 seconds limit)."
    except Exception as e:
        return f"System error: {str(e)}"