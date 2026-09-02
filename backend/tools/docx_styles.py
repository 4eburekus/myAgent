"""Общий модуль стилей для .docx документов.

ВНИМАНИЕ: стили продублированы из styles.py (файл не трогаем). Если меняете
стили здесь — синхронизируйте с styles.py (и наоборот), чтобы не было расхождений.

Отличие от styles.py: чистые функции без сайд-эффектов.
- add_styles(doc) — определяет стили на переданном документе
- add_image(doc, image_path, img_counter, ...) — картинка + подпись, счётчик параметром
- add_table(doc, name_table, data, widths, table_counter, ...) — таблица, счётчик параметром
"""
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING, WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from io import BytesIO
import os
from PIL import Image
from docx.enum.table import WD_ALIGN_VERTICAL


def add_styles(doc: Document) -> None:
    """Определяет все стили документа (копия из styles.py).

    Идемпотентна: если стили уже добавлены ранее (маркер — наличие 'normalText'),
    повторно не добавляет. Это позволяет вызывать её для уже существующих
    документов (например, перед вставкой титульника).
    """
    styles = doc.styles

    # Уже добавлены — выходим
    try:
        styles['normalText']
        return
    except KeyError:
        pass

    # -----------------------Обычный текст-----------------------------
    nt = styles.add_style('normalText', WD_STYLE_TYPE.PARAGRAPH)
    nt.font.name = 'Times New Roman'
    nt.font.size = Pt(14)
    nt.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    nt.paragraph_format.left_indent = Cm(-1)
    nt.paragraph_format.first_line_indent = Cm(1.25)
    nt.paragraph_format.line_spacing = 1.5
    nt.paragraph_format.space_before = Pt(12)
    nt.paragraph_format.space_after = Pt(6)
    nt.paragraph_format.widow_control = True
    nt.quick_style = True

    # -----------------------Заголовки-----------------------------
    h1 = styles.add_style('heading1', WD_STYLE_TYPE.PARAGRAPH)
    h1.base_style = styles['Normal']
    h1.font.name = 'Times New Roman'
    h1.font.size = Pt(20)
    h1.font.bold = True
    h1.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    h1.paragraph_format.line_spacing = 1.0
    h1.paragraph_format.keep_with_next = True
    h1.paragraph_format.widow_control = True
    h1.next_paragraph_style = styles['Normal']
    h1.quick_style = True

    h2 = styles.add_style('heading2', WD_STYLE_TYPE.PARAGRAPH)
    h2.base_style = styles['Normal']
    h2.font.name = 'Times New Roman'
    h2.font.size = Pt(18)
    h2.font.bold = True
    h2.paragraph_format.first_line_indent = Cm(0.5)
    h2.paragraph_format.keep_with_next = True
    h2.quick_style = True

    h3 = styles.add_style('heading3', WD_STYLE_TYPE.PARAGRAPH)
    h3.base_style = styles['Normal']
    h3.font.name = 'Times New Roman'
    h3.font.size = Pt(14)
    h3.font.bold = True
    h3.paragraph_format.first_line_indent = Cm(0.8)
    h3.paragraph_format.keep_with_next = True
    h3.quick_style = True

    # -----------------------Часть кода-----------------------------
    code = styles.add_style('code', WD_STYLE_TYPE.PARAGRAPH)
    code.font.name = 'Times New Roman'
    code.font.size = Pt(12)
    code.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    code.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    code.paragraph_format.line_spacing = 1.08
    code.paragraph_format.widow_control = True
    pPr = code._element.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    for border in ['top', 'left', 'bottom', 'right']:
        node = OxmlElement(f'w:{border}')
        node.set(qn('w:val'), 'single')
        node.set(qn('w:sz'), '2')  # ширина границы рамки 0.25 pt (в 1/8 пункта)
        node.set(qn('w:space'), '4')
        node.set(qn('w:color'), 'auto')
        pBdr.append(node)
    pPr.append(pBdr)
    code.quick_style = True

    # -----------------------Картинки-----------------------------
    img_style = styles.add_style('image', WD_STYLE_TYPE.PARAGRAPH)
    img_style.base_style = nt
    img_style.paragraph_format.left_indent = Cm(-1)
    img_style.paragraph_format.right_indent = Cm(-0.25)
    img_style.paragraph_format.first_line_indent = Cm(0)
    img_style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    img_style.paragraph_format.keep_with_next = True
    img_style.quick_style = True

    # -----------------------Списки-----------------------------
    # listBig нумерованый
    l_big = styles.add_style('listBig', WD_STYLE_TYPE.PARAGRAPH)
    l_big.base_style = nt
    l_big.paragraph_format.left_indent = Cm(1)
    l_big.paragraph_format.first_line_indent = Cm(-0.63)
    l_big.paragraph_format.space_before = Pt(0)
    l_big.paragraph_format.space_after = Pt(0)
    # listMid маркированный *
    l_mid = styles.add_style('listMid', WD_STYLE_TYPE.PARAGRAPH)
    l_mid.base_style = nt
    l_mid.paragraph_format.left_indent = Cm(1 + 0.8)
    l_mid.paragraph_format.first_line_indent = Cm(-0.63)
    l_mid.paragraph_format.space_before = Pt(0)
    l_mid.paragraph_format.space_after = Pt(0)
    # listSmall маркированный -
    l_small = styles.add_style('listSmall', WD_STYLE_TYPE.PARAGRAPH)
    l_small.base_style = nt
    l_small.paragraph_format.left_indent = Cm(1 + 1.2)
    l_small.paragraph_format.first_line_indent = Cm(-0.63)
    l_small.paragraph_format.space_before = Pt(0)
    l_small.paragraph_format.space_after = Pt(0)

    # -----------------------Таблицы-----------------------------
    # Форматирование границ происходит уже в исполняемом инструменте
    # Название таблицы
    t_name = styles.add_style('tableName', WD_STYLE_TYPE.PARAGRAPH)
    t_name.base_style = styles['Normal']
    t_name.font.name = 'Times New Roman'
    t_name.font.size = Pt(14)
    t_name.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    t_name.next_paragraph_style = styles['Normal']
    t_name.paragraph_format.space_before = Pt(0)
    t_name.paragraph_format.space_after = Pt(0)
    # Стиль для шапки таблицы
    t_header = styles.add_style('tableHeader', WD_STYLE_TYPE.PARAGRAPH)
    t_header.font.name = 'Times New Roman'
    t_header.font.size = Pt(12)
    t_header.font.bold = True
    t_header.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t_header.paragraph_format.space_before = Pt(0)
    t_header.paragraph_format.space_after = Pt(0)
    # Стиль для обычных ячеек
    t_body = styles.add_style('tableBody', WD_STYLE_TYPE.PARAGRAPH)
    t_body.font.name = 'Times New Roman'
    t_body.font.size = Pt(12)
    t_body.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    t_body.paragraph_format.space_before = Pt(2)
    t_body.paragraph_format.space_after = Pt(2)

    # -----------------------Ошибка в коде-----------------------------
    er = styles.add_style('error', WD_STYLE_TYPE.PARAGRAPH)
    er.base_style = styles['Normal']
    er.font.name = 'Times New Roman'
    er.font.size = Pt(26)
    er.font.highlight_color = WD_COLOR_INDEX.RED
    er.font.bold = True
    er.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    er.next_paragraph_style = styles['Normal']

    # -----------------------Для титульника-----------------------------
    tt1 = styles.add_style('titleText1', WD_STYLE_TYPE.PARAGRAPH)
    tt1.font.name = 'Times New Roman'
    tt1.font.size = Pt(14)
    tt1.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    tt1.paragraph_format.line_spacing = 1.5
    tt1.paragraph_format.space_before = Pt(0)
    tt1.paragraph_format.space_after = Pt(0)

    tt2 = styles.add_style('titleText2', WD_STYLE_TYPE.PARAGRAPH)
    tt2.font.name = 'Times New Roman'
    tt2.font.size = Pt(14)
    tt2.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    tt2.paragraph_format.line_spacing = 1.5
    tt2.paragraph_format.space_before = Pt(12)
    tt2.paragraph_format.space_after = Pt(6)
    tt2.font.bold = True

    tt3 = styles.add_style('titleText3', WD_STYLE_TYPE.PARAGRAPH)
    tt3.font.name = 'Times New Roman'
    tt3.font.size = Pt(14)
    tt3.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    tt3.paragraph_format.line_spacing = 1.5
    tt3.paragraph_format.space_before = Pt(0)
    tt3.paragraph_format.space_after = Pt(0)


def add_image(doc: Document, image_path: str, img_counter: int,
              available_width_cm: float = 17.25, max_height_cm: float = 21.0,
              style: str = 'image', styleError: str = 'error') -> int:
    """Добавляет в документ картинку и её подпись с порядковым номером.

    Возвращает обновлённый счётчик картинок (img_counter + 1).
    При ошибке вставляет абзац со стилем 'error' (счётчик тоже увеличивается).
    """
    img_counter += 1
    try:
        file_name = os.path.basename(image_path)
        clean_name = os.path.splitext(file_name)[0]

        if len(clean_name) >= 41:
            raise ValueError(f"Название файла '{clean_name}' слишком длинное ({len(clean_name)} симв.). Максимум 41.")

        with Image.open(image_path) as img:
            orig_w, orig_h = img.size
            ratio = available_width_cm / orig_w
            scaled_height = orig_h * ratio
            if scaled_height > max_height_cm:
                new_h_px = int(max_height_cm / ratio)
                img = img.crop((0, 0, orig_w, new_h_px))
            image_stream = BytesIO()
            img.save(image_stream, format='PNG')
            image_stream.seek(0)

        p_img = doc.add_paragraph(style=style)
        run = p_img.add_run()
        run.add_picture(image_stream, width=Cm(available_width_cm))

        caption_text = f"Рис. {img_counter}. {clean_name}."
        doc.add_paragraph(caption_text, style=style)
    except Exception as e:
        name_for_error = clean_name if 'clean_name' in locals() else image_path
        error_message = f"ОШИБКА В РИС. {img_counter}: {str(e)}\n"
        doc.add_paragraph(error_message, styleError)

    return img_counter


def add_table(doc: Document, name_table: str, data, widths,
              table_counter: int,
              styleTableName: str = 'tableName',
              styleTableHeader: str = 'tableHeader',
              styleTableBody: str = 'tableBody',
              styleError: str = 'error') -> int:
    """Добавляет таблицу в документ с проверками и сложным форматированием.

    - data: двумерный массив (строка 0 — заголовки, остальные — тело)
    - widths: пропорции столбцов, [Cm(...), Cm(...), ...]
    Возвращает обновлённый счётчик таблиц (table_counter + 1).
    При ошибке вставляет абзац со стилем 'error'.
    """
    table_counter += 1
    try:
        if len(name_table) > 34:
            raise ValueError(f"Название таблицы слишком длинное ({len(name_table)} симв.). Макс: 34.")
        max_row_len = max(len(row) for row in data)
        if len(data[0]) < max_row_len:
            raise ValueError("Количество элементов в заголовочной строке (data[0]) должно быть максимальным.")
        if len(widths) != len(data[0]):
            raise ValueError(f"Количество ширин ({len(widths)}) не совпадает с количеством столбцов ({len(data[0])}).")

        doc.add_paragraph(f"Таб. {table_counter}. {name_table}.", style=styleTableName)
        table = doc.add_table(rows=len(data), cols=len(data[0]))
        table.style = 'Table Grid'
        table.allow_autofit = False
        for i, width_val in enumerate(widths):
            for cell in table.columns[i].cells:
                cell.width = width_val

        for r_idx, row_data in enumerate(data):
            for c_idx, text in enumerate(row_data):
                cell = table.cell(r_idx, c_idx)
                cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

                p = cell.paragraphs[0]
                p.text = str(text)

                if r_idx == 0:
                    p.style = styleTableHeader
                    tcPr = cell._tc.get_or_add_tcPr()
                    shd = OxmlElement('w:shd')
                    shd.set(qn('w:val'), 'clear')
                    shd.set(qn('w:color'), 'auto')
                    shd.set(qn('w:fill'), 'E6E6E6')
                    tcPr.append(shd)
                else:
                    p.style = styleTableBody

        left_indent_twips = -567
        total_width_twips = 10064

        tblPr = table._element.xpath('w:tblPr')[0]
        indents = tblPr.xpath('w:tblInd')
        if indents:
            tblPr.remove(indents[0])
        tblInd = OxmlElement('w:tblInd')
        tblInd.set(qn('w:w'), str(left_indent_twips))
        tblInd.set(qn('w:type'), 'dxa')
        tblPr.append(tblInd)

        t_widths = tblPr.xpath('w:tblW')
        if t_widths:
            tblPr.remove(t_widths[0])
        tblW = OxmlElement('w:tblW')
        tblW.set(qn('w:w'), str(total_width_twips))
        tblW.set(qn('w:type'), 'dxa')
        tblPr.append(tblW)

        layouts = tblPr.xpath('w:tblLayout')
        if layouts:
            tblPr.remove(layouts[0])
        tblLayout = OxmlElement('w:tblLayout')
        tblLayout.set(qn('w:type'), 'fixed')
        tblPr.append(tblLayout)
    except Exception as e:
        error_p = doc.add_paragraph(style=styleError)
        run = error_p.add_run(f"ОШИБКА ТАБЛИЦЫ: {str(e)}\n")
        error_p.add_run(f"Таб. {table_counter}. {name_table}")

    return table_counter


def add_title_page(doc: Document,
                   discipline: str, workName: str, workTheme: str,
                   positionInspector: str, inspector: str,
                   workers: list, workersGroup: str = "23-ИСбо-4б",
                   insert_at_beginning: bool = False) -> None:
    """Добавляет в документ титульную страницу.

    Аргументы:
    - doc: объект документа (python-docx)
    - discipline: название дисциплины
    - workName: название работы (например: "Лабораторная работа №3")
    - workTheme: тема работы
    - positionInspector: должность проверяющего
    - inspector: ФИО проверяющего
    - workers: список людей, выполняющих работу (например: ["Кузнецов Павел Михайлович", "Пылова Виктория Дмитриевна"])
    - workersGroup: название группы
    - insert_at_beginning: если True — титульник вставляется в НАЧАЛО документа
      (даже если документ уже содержит контент). Иначе — добавляется в конец.
    """
    # Если документ пустой или добавляем в конец — собираем прямо в нём
    if not insert_at_beginning or not doc.paragraphs:
        _add_title_paragraphs(doc, discipline, workName, workTheme,
                              positionInspector, inspector, workers, workersGroup)
        return

    # Вставка в начало существующего документа: собираем титульник во временном
    # документе (стили уже есть в целевом — они идемпотентны), затем переносим
    # XML-элементы в начало целевого документа.
    temp = Document()
    add_styles(temp)
    _add_title_paragraphs(temp, discipline, workName, workTheme,
                          positionInspector, inspector, workers, workersGroup)

    target_body = doc.element.body
    # Находим первый дочерний элемент body (не sectPr — свойства секции)
    first_child = None
    for child in target_body:
        if child.tag != qn('w:sectPr'):
            first_child = child
            break

    for el in list(temp.element.body):
        if el.tag == qn('w:sectPr'):
            continue  # свойства секции временного документа не переносим
        if first_child is not None:
            first_child.addprevious(el)
        else:
            target_body.append(el)


def _add_title_paragraphs(doc: Document,
                          discipline: str, workName: str, workTheme: str,
                          positionInspector: str, inspector: str,
                          workers: list, workersGroup: str) -> None:
    """Внутренняя функция: добавляет абзацы титульника в конец doc (как в styles.py)."""
    import datetime

    # --- 1. ШАПКА (Университет и дисциплина) ---
    header_text = (
        "МИНОБРНАУКИ РОССИИ\n"
        "Федеральное государственное бюджетное образовательное учреждение высшего образования\n"
        "«Костромской государственный университет» (КГУ)\n"
        "Институт Высшая ИТ-Школа\n"
        "Кафедра информационных систем и технологий\n"
        "Направление подготовки 09.03.02\n"
        "Профиль Поддержка и развитие IT-инфраструктуры компаний\n"
        f"Дисциплина «{discipline}»"
    )
    doc.add_paragraph(header_text, style="titleText1")

    # --- 2. НАЗВАНИЕ РАБОТЫ ---
    doc.add_paragraph(f"{workName}\n{workTheme}", style="titleText2")

    # --- 3. РАСПОРКА (Пустые параграфы) ---
    base_spacer = 8
    dynamic_spacer = base_spacer - len(workers)
    # Страховка, чтобы не уйти в отрицательное число
    if dynamic_spacer <= 1:
        dynamic_spacer = 1
    else:
        doc.add_paragraph("\n" * (dynamic_spacer - 1))

    # --- 4. БЛОК ИСПОЛНИТЕЛЕЙ И ПРОВЕРЯЮЩЕГО ---
    # Формируем список студентов циклом (запятая после каждого, кроме последнего)
    workers_str = ",\n".join(workers)
    info_block = (
        f"Выполнили студенты\n"
        f"{workers_str}\n"
        f"Группа {workersGroup}\n"
        f"Проверил {positionInspector}\n"
        f"{inspector}\n"
        f"Оценка __________________________\n"
        f"Подпись преподавателя ____________"
    )
    doc.add_paragraph(info_block, style="titleText3")

    # --- 5. НИЗ (Город и год) ---
    current_year = datetime.datetime.now().year
    doc.add_paragraph(f"Кострома\n{current_year}", style="titleText1")
    # Разрыв страницы, чтобы следующий текст начался с нового листа
    doc.add_page_break()
