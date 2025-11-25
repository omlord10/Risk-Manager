from models import RiskNode

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, LongTable, TableStyle, Paragraph, Spacer
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    # Регистрируем все варианты Times New Roman
    pdfmetrics.registerFont(TTFont("Times-Roman", "fonts/times.ttf"))        # обычный
    pdfmetrics.registerFont(TTFont("Times-Bold", "fonts/timesbd.ttf"))        # жирный
    pdfmetrics.registerFont(TTFont("Times-Italic", "fonts/timesi.ttf"))       # курсив
    pdfmetrics.registerFont(TTFont("Times-BoldItalic", "fonts/timesbi.ttf"))  # жирный курсив

    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# Стиль для ячеек с переносом текста
cell_style = ParagraphStyle(
    name="Cell",
    fontName="Times-Roman",
    fontSize=9,
    leading=11,  # расстояние между строками
    wordWrap="CJK"
)

def generate_pdf(
        nodes: list[RiskNode],
        sort_column="Risk",
        sort_order="Убыванию",
        filename="data/risk_report_magnit.pdf"
):
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("ReportLab не установлен")

    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.pagesizes import A4


    doc = SimpleDocTemplate(filename, pagesize=A4,
                            leftMargin=30, rightMargin=30,
                            topMargin=30, bottomMargin=30)

    PAGE_WIDTH, PAGE_HEIGHT = A4
    table_width = PAGE_WIDTH - doc.leftMargin - doc.rightMargin - 10  # минус 1 см справа

    # Колонки разной ширины
    col_widths = [
        table_width * 0.17,  # Объект/Город
        table_width * 0.07,  # P
        table_width * 0.10,  # Lmin
        table_width * 0.10,  # Lmax
        table_width * 0.13,  # ExpectedMin
        table_width * 0.13,  # ExpectedMax
        table_width * 0.10,  # Severity
        table_width * 0.13   # Risk
    ]

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TitleTimes", parent=styles["Title"],
                              fontName="Times-Bold", fontSize=16))
    styles.add(ParagraphStyle(name="NormalTimes", parent=styles["Normal"],
                              fontName="Times-Roman", fontSize=10))

    elems = []

    # Заголовок
    elems.append(Paragraph("Отчёт ПАО 'МАГНИТ'", styles["TitleTimes"]))
    elems.append(Spacer(1, 6))
    elems.append(Paragraph("Модель: Lmin/Lmax × P, Risk = P × Severity", styles["NormalTimes"]))
    elems.append(Spacer(1, 6))

    # Пояснение переменных
    elems.append(Paragraph("Обозначения переменных:", styles["NormalTimes"]))
    elems.append(Paragraph(
        "<b>P</b> — вероятность, "
        "<b>Lmin/Lmax</b> — мин/макс потери, "
        "<b>ExpectedMin/ExpectedMax</b> — ожидаемые мин/макс потери, "
        "<b>Severity</b> — тяжесть, ",
        cell_style
    ))
    elems.append(Paragraph(
        "<b>Risk</b> — риск = P × Severity",
        cell_style
    ))
    elems.append(Spacer(1, 12))

    # Колонки с русскими названиями
    COLUMN_NAMES = ["Объект", "P", "Lmin", "Lmax", "ExpectedMin", "ExpectedMax", "Severity", "Risk"]

    # Сопоставление русских названий из UI с ключами для сортировки
    UI_TO_KEY = {
        "Объект": "Объект",
        "Вероятность": "P",
        "Мин. потери": "Lmin",
        "Макс. потери": "Lmax",
        "Ожидаемый мин. потери": "ExpectedMin",
        "Ожидаемый макс. потери": "ExpectedMax",
        "Вес": "Severity",
        "Риск": "Risk"
    }

    sort_key = UI_TO_KEY.get(sort_column, "Risk")
    reverse = sort_order == "Убыванию"

    # Для отображения в заголовках таблиц используем исходное название из combobox
    KEY_TO_UI = {v: k for k, v in UI_TO_KEY.items()}
    header_sort_name = KEY_TO_UI.get(sort_key, sort_column)

    def get_key(n):
        mapping = {
            "P": n.prob,
            "Lmin": n.loss_min,
            "Lmax": n.loss_max,
            "ExpectedMin": (n.prob or 0.0)*(n.loss_min or 0.0),
            "ExpectedMax": (n.prob or 0.0)*(n.loss_max or 0.0),
            "Severity": n.severity,
            "Risk": (n.prob or 0.0)*(n.severity or 1.0)
        }
        return mapping.get(sort_key, 0)

    # --- Таблица 1 — города ---
    cities = cities = [n for n in nodes if n.name.startswith("г.")]
    elems.append(Paragraph(
        f'Таблица № 1 — Средние значения в ПАО "МАГНИТ" по городам ({header_sort_name}, {"убыв." if reverse else "возр."})',
        styles["NormalTimes"]
    ))
    elems.append(Spacer(1, 6))

    city_data = [COLUMN_NAMES]
    for city in cities:
        lower = (city.prob or 0.0)*(city.loss_min or 0.0)
        upper = (city.prob or 0.0)*(city.loss_max or 0.0)
        risk = (city.prob or 0.0)*(city.severity or 1.0)
        city_data.append([
            Paragraph(city.name, cell_style),
            Paragraph(f"{city.prob:.3f}", cell_style),
            Paragraph(f"{city.loss_min:.2f}", cell_style),
            Paragraph(f"{city.loss_max:.2f}", cell_style),
            Paragraph(f"{lower:.2f}", cell_style),
            Paragraph(f"{upper:.2f}", cell_style),
            Paragraph(f"{city.severity:.1f}", cell_style),
            Paragraph(f"{risk:.2f}", cell_style)
        ])

    table_style = [("FONTNAME", (0,0), (-1,-1), "Times-Roman"),
                   ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
                   ("GRID", (0,0), (-1,-1), 0.5, colors.grey)]
    for i, row in enumerate(city_data[1:], start=1):
        risk_val = float(row[7].text)
        if 1 <= risk_val < 2.5:
            table_style.append(("BACKGROUND", (7,i), (7,i), colors.lightgreen))
        elif 2.5 <= risk_val < 4:
            table_style.append(("BACKGROUND", (7,i), (7,i), colors.yellow))
        elif 4 <= risk_val <= 5:
            table_style.append(("BACKGROUND", (7,i), (7,i), colors.red))

    table = LongTable(city_data, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle(table_style))
    elems.append(table)
    elems.append(Spacer(1, 12))

    # --- Таблицы объектов в городах ---
    table_idx = 2
    for city in cities:
        objects = [n for n in nodes if n.id in city.children]
        if not objects:
            continue

        elems.append(Paragraph(
            f"Таблица № {table_idx} — Средние значения в {city.name} ({header_sort_name}, {'убыв.' if reverse else 'возр.'})",
            styles["NormalTimes"]
        ))
        elems.append(Spacer(1, 6))
        table_idx += 1

        data = [COLUMN_NAMES]
        for obj in objects:
            lower = (obj.prob or 0.0)*(obj.loss_min or 0.0)
            upper = (obj.prob or 0.0)*(obj.loss_max or 0.0)
            risk = (obj.prob or 0.0)*(obj.severity or 1.0)
            data.append([
                Paragraph(obj.name, cell_style),
                Paragraph(f"{obj.prob:.3f}", cell_style),
                Paragraph(f"{obj.loss_min:.2f}", cell_style),
                Paragraph(f"{obj.loss_max:.2f}", cell_style),
                Paragraph(f"{lower:.2f}", cell_style),
                Paragraph(f"{upper:.2f}", cell_style),
                Paragraph(f"{obj.severity:.1f}", cell_style),
                Paragraph(f"{risk:.2f}", cell_style)
            ])

        table_style = [("FONTNAME", (0,0), (-1,-1), "Times-Roman"),
                       ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
                       ("GRID", (0,0), (-1,-1), 0.5, colors.grey)]
        for i,row in enumerate(data[1:], start=1):
            risk_val = float(row[7].text)
            if 1 <= risk_val < 2.5:
                table_style.append(("BACKGROUND", (7,i), (7,i), colors.lightgreen))
            elif 2.5 <= risk_val < 4:
                table_style.append(("BACKGROUND", (7,i), (7,i), colors.yellow))
            elif 4 <= risk_val <= 5:
                table_style.append(("BACKGROUND", (7,i), (7,i), colors.red))

        table = LongTable(data, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
        table.setStyle(TableStyle(table_style))
        elems.append(table)
        elems.append(Spacer(1, 12))

    doc.build(elems)
