from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING, WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
# Для добавления картинки
import os
from io import BytesIO
from PIL import Image
# Для таблиц
from docx.enum.table import WD_ALIGN_VERTICAL


doc = Document()
styles = doc.styles

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




# --- ТЕСТОВОЕ ЗАПОЛНЕНИЕ ---

doc.add_paragraph("Заголовок первого уровня", style='heading1')

doc.add_paragraph(
    "Это основной текст (normalText). У него отрицательный отступ слева -1см, "
    "выравнивание по ширине и красная строка 1.25см.", 
    style='normalText'
)

doc.add_paragraph("Заголовок второго уровня", style='heading2')

# Списки
doc.add_paragraph("1. большой элемент списка 1", style='listBig')
doc.add_paragraph("2. большой элемент списка 2", style='listBig')
doc.add_paragraph("* средний элемент списка 1", style='listMid')
doc.add_paragraph("* средний элемент списка 2", style='listMid')
doc.add_paragraph("- малый элемент списка 1", style='listSmall')
doc.add_paragraph("- малый элемент списка 2", style='listSmall')
doc.add_paragraph("* средний элемент списка 3", style='listMid')
doc.add_paragraph("3. большой элемент списка 3", style='listBig')

doc.add_paragraph("Пример блока кода с рамкой:", style='normalText')
doc.add_paragraph(
    """doc.add_paragraph("1. большой элемент списка 1", style='listBig')
doc.add_paragraph("2. большой элемент списка 2", style='listBig')
doc.add_paragraph("* средний элемент списка 1", style='listMid')
doc.add_paragraph("* средний элемент списка 2", style='listMid')
doc.add_paragraph("- малый элемент списка 1", style='listSmall')
doc.add_paragraph("- малый элемент списка 2", style='listSmall')
doc.add_paragraph("* средний элемент списка 3", style='listMid')
doc.add_paragraph("3. большой элемент списка 3", style='listBig')""", 
    style='code'
)

doc.add_paragraph("Заголовок третьего уровня", style='heading3')
doc.add_paragraph(
    """doc.add_paragraph("1. большой элемент списка 1", style='listBig')
doc.add_paragraph("3. большой элемент списка 3", style='listBig')""", 
    style='code'
)
# ---------------------------------------------------------
# ------------Работа с картинками--------------------------
# ---------------------------------------------------------


img_counter = 0
def add_image(doc, image_path, available_width_cm=17.25, max_height_cm=21.0, style='image', styleError='error'):
    """Добавляет в документ картинку и ее подпись с указанием порядкового номера. Функция зависит от глобальной переменной.
    Аргументы:
    - doc: переменная документа
    - image_path: название файла
    - available_width_cm=17.25: предпочтительная ширина (задана под поля документа)
    - max_height_cm=21.0: максимальная высота (если больше - картинка обрезается снизу)
    - style='image': стиль документа для вставки картинки
    - styleError='error': стиль документа для ошибки"""
    global img_counter
    img_counter += 1
    try:
        # os.path.basename берет 'Название.png', а splitext отделяет '.png'
        file_name = os.path.basename(image_path)
        clean_name = os.path.splitext(file_name)[0]

        if len(clean_name) >= 41:
            raise ValueError(f"Название файла '{clean_name}' слишком длинное ({len(clean_name)} симв.). Максимум 41.")

        with Image.open(image_path) as img:
            orig_w, orig_h = img.size # Размер в пикселях
            # Вычисление высоты при заданной ширине
            # k = целевая_ширина / текущая_ширина
            ratio = available_width_cm / orig_w
            scaled_height = orig_h * ratio
            # Если высота превышает лимит - обрезаем
            if scaled_height > max_height_cm:
                # Вычисляем, сколько пикселей по высоте соответствуют лимиту в 21 см
                # h_px = max_height_cm / ratio
                new_h_px = int(max_height_cm / ratio)
                # Обрезаем: (лево, верх, право, низ)
                img = img.crop((0, 0, orig_w, new_h_px))
            # Сохраняем обработанное изображение во временный буфер (в память)
            # чтобы не создавать лишних файлов на диске
            image_stream = BytesIO()
            img.save(image_stream, format='PNG') # Сохраняем как PNG для качества
            image_stream.seek(0)

        p_img = doc.add_paragraph(style=style)
        run = p_img.add_run()
        run.add_picture(image_stream, width=Cm(available_width_cm))

        caption_text = f"Рис. {img_counter}. {clean_name}."
        doc.add_paragraph(caption_text, style=style)
    except Exception as e:
        name_for_error = clean_name if 'clean_name' in locals() else image_path
        error_message = (
            f"ОШИБКА В РИС. {img_counter}: {str(e)}\n"
        )
        doc.add_paragraph(error_message, styleError)

doc.add_paragraph("Ниже следуют картинки.", style='normalText')
add_image(doc, 'stet2.jpg')
add_image(doc, 'BongoCat_cugDoJ6Ueu.png')




# ---------------------------------------------------------
# ------------Работа с таблицами--------------------------
# ---------------------------------------------------------

# Глобальный счетчик таблиц
table_counter = 0
def add_table(doc, name_table, data, widths, styleTableName='tableName', styleTableHeader='tableHeader', styleTableBody='tableBody',styleError='error'):
    """Добавляет таблицу в документ с проверками и сложным форматированием. Функция зависит от глобальной переменной.
    Аргументы:
    - doc: переменная документа
    - name_table: название таблицы
    - data: двумерный массив данных
    - widths: пропорции столбцов, подаются в формате [Cm(значение), Cm(значение), Cm(значение)]
    - styleTableName='tableName': стиль документа для названия идущего перед таблицей
    - styleTableHeader='tableHeader': стиль документа для текста в шапке таблицы
    - styleTableBody='tableBody': стиль документа для текста в теле таблицы
    - styleError='error': стиль документа для ошибки"""
    global table_counter
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
        # Установка ширин столбцов (из аргумента widths)
        for i, width_val in enumerate(widths):
            for cell in table.columns[i].cells:
                cell.width = width_val

        # Заполнение данными и стилизация
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

        # XML-настройка границ (растягивание)
        left_indent_twips = -567
        total_width_twips = 10064

        tblPr = table._element.xpath('w:tblPr')[0]
        # Установка tblInd (Левый отступ)
        indents = tblPr.xpath('w:tblInd')
        if indents: tblPr.remove(indents[0])
        tblInd = OxmlElement('w:tblInd')
        tblInd.set(qn('w:w'), str(left_indent_twips))
        tblInd.set(qn('w:type'), 'dxa')
        tblPr.append(tblInd)
        # Установка tblW (Общая фиксированная ширина)
        t_widths = tblPr.xpath('w:tblW')
        if t_widths: tblPr.remove(t_widths[0])
        tblW = OxmlElement('w:tblW')
        tblW.set(qn('w:w'), str(total_width_twips))
        tblW.set(qn('w:type'), 'dxa')
        tblPr.append(tblW)
        # Установка tblLayout (Фиксированный макет)
        layouts = tblPr.xpath('w:tblLayout')
        if layouts: tblPr.remove(layouts[0])
        tblLayout = OxmlElement('w:tblLayout')
        tblLayout.set(qn('w:type'), 'fixed')
        tblPr.append(tblLayout)
    except Exception as e:
        error_p = doc.add_paragraph(style=styleError)
        run = error_p.add_run(f"ОШИБКА ТАБЛИЦЫ: {str(e)}\n")
        error_p.add_run(f"Таб. {table_counter}. {name_table}")

# --- ТЕСТОВЫЙ ВЫЗОВ ---
# Данные
my_data = [
    ["№", "Параметр", ""],
    ["1", "Длина кабеля", "50 м"],
    ["2", "Сопротивление", "0.5 Ом"]
]
# пропорции ширин столбцов
my_widths = [Cm(1), Cm(4), Cm(1)] 
# Вызов функции
add_table(doc, "Технические характеристики", my_data, my_widths)
add_table(doc, "Технические характеристики", my_data, my_widths)




doc.add_paragraph("Конец тестового документа.", style='normalText')
doc.save('final_combined_document.docx')
print("Документ успешно сохранен.")