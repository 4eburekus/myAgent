from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

doc = Document()
styles = doc.styles

# --- 1. СТИЛЬ: normalText (База для многих стилей) ---
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

# --- 2. СТИЛИ: Заголовки ---
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

# --- 3. СТИЛЬ: code (Код с рамкой) ---
code = styles.add_style('code', WD_STYLE_TYPE.PARAGRAPH)
code.font.name = 'Times New Roman'
code.font.size = Pt(12)
code.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
code.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
code.paragraph_format.line_spacing = 1.08
code.paragraph_format.widow_control = True
def set_paragraph_border(style):
    """Добавляет одинарную рамку 0.25 пт вокруг абзаца."""
    pPr = style._element.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    for border in ['top', 'left', 'bottom', 'right']:
        node = OxmlElement(f'w:{border}')
        node.set(qn('w:val'), 'single')
        node.set(qn('w:sz'), '2')  # 0.25 pt (в 1/8 пункта)
        node.set(qn('w:space'), '4')
        node.set(qn('w:color'), 'auto')
        pBdr.append(node)
    pPr.append(pBdr)
set_paragraph_border(code)
code.quick_style = True

# --- 4. СТИЛЬ: image ---
img_style = styles.add_style('image', WD_STYLE_TYPE.PARAGRAPH)
img_style.base_style = nt
img_style.paragraph_format.left_indent = Cm(-1)
img_style.paragraph_format.right_indent = Cm(-0.25)
img_style.paragraph_format.first_line_indent = Cm(0)
img_style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
img_style.paragraph_format.keep_with_next = True
img_style.quick_style = True

# --- 5. СТИЛИ: Списки (Имитация) ---
# listBig
l_big = styles.add_style('listBig', WD_STYLE_TYPE.PARAGRAPH)
l_big.base_style = nt
l_big.paragraph_format.left_indent = Cm(1)
l_big.paragraph_format.first_line_indent = Cm(-0.63)
l_big.paragraph_format.space_before = Pt(0)
l_big.paragraph_format.space_after = Pt(0)

# listMid
l_mid = styles.add_style('listMid', WD_STYLE_TYPE.PARAGRAPH)
l_mid.base_style = nt
l_mid.paragraph_format.left_indent = Cm(1 + 0.8)
l_mid.paragraph_format.first_line_indent = Cm(-0.63)
l_mid.paragraph_format.space_before = Pt(0)
l_mid.paragraph_format.space_after = Pt(0)

# listSmall
l_small = styles.add_style('listSmall', WD_STYLE_TYPE.PARAGRAPH)
l_small.base_style = nt
l_small.paragraph_format.left_indent = Cm(1 + 1.2)
l_small.paragraph_format.first_line_indent = Cm(-0.63)
l_small.paragraph_format.space_before = Pt(0)
l_small.paragraph_format.space_after = Pt(0)

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

# Картинка
# Расчет ширины: стандартное поле (~16см) + компенсация ваших отступов (1см + 0.25см)
available_width = Cm(16) + Cm(1) + Cm(0.25) # Примерный расчет для стандартных полей
# available_height = Cm(21) # Чтобы под картинкой во всю страницу уместилась подпись

def add_picture(doc, image_path, text_picture, available_width=Cm(17.25), style='image'):
    f
    f
    f
    f
add_picture(doc, 'BongoCat_cugDoJ6Ueu.png')

try:
    p_img = doc.add_paragraph(style='image')
    run = p_img.add_run()
    # При добавлении картинки лучше указывать только ширину, чтобы сохранить пропорции
    run.add_picture('BongoCat_cugDoJ6Ueu.png', width=available_width)
    doc.add_paragraph("Картинка 1.", style='image')
    doc.add_paragraph("Конец тестового документа.", style='normalText')

    run.add_picture('Картинка.jpg', width=available_width) 

except Exception as e:
    doc.add_paragraph(f"Здесь должна быть картинка (Файл stet2.jpg не найден)", style='normalText')

doc.add_paragraph("Конец тестового документа.", style='normalText')

doc.save('final_combined_document.docx')
print("Документ успешно сохранен.")