from models import RiskNode

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
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

def generate_pdf(nodes: list[RiskNode], filename="data/risk_report_magnit.pdf"):
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("ReportLab не установлен")

    # --- Подготовка PDF ---
    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        leftMargin=30, rightMargin=30, topMargin=30, bottomMargin=30
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TitleTimes", parent=styles["Title"], fontName="Times-Bold", fontSize=16))
    styles.add(ParagraphStyle(name="NormalTimes", parent=styles["Normal"], fontName="Times-Roman", fontSize=10))

    elems = []
    elems.append(Paragraph("Отчёт по рискам — ПАО 'МАГНИТ'", styles["TitleTimes"]))
    elems.append(Spacer(1, 6))
    elems.append(Paragraph("Модель: Lmin/Lmax × P, Risk = P × Severity", styles["NormalTimes"]))
    elems.append(Spacer(1, 12))

    # --- Сначала таблица по городам ---
    data = [["Город", "P", "Lmin", "Lmax", "Lower", "Upper", "Severity", "Risk"]]

    # Города — определяем по имени, если первые 2 буквы "г."
    cities = [n for n in nodes if n.name.startswith("г.")]

    for city in cities:
        lower = (city.prob or 0.0) * (city.loss_min or 0.0)
        upper = (city.prob or 0.0) * (city.loss_max or 0.0)
        risk = (city.prob or 0.0) * (city.severity or 1.0)

        data.append([
            city.name,
            f"{city.prob:.3f}",
            f"{city.loss_min:.2f}",
            f"{city.loss_max:.2f}",
            f"{lower:.2f}",
            f"{upper:.2f}",
            f"{city.severity:.1f}",
            f"{risk:.2f}",
        ])

    table = Table(data, colWidths=[150, 40, 60, 60, 60, 60, 50, 50], repeatRows=1)
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Times-Roman"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))

    elems.append(table)
    elems.append(Spacer(1, 12))

    # --- Таблицы объектов внутри каждого города ---
    for city in cities:
        elems.append(Paragraph(f"Город: {city.name}", styles["NormalTimes"]))
        elems.append(Spacer(1, 6))

        data = [["Объект", "P", "Lmin", "Lmax", "Lower", "Upper", "Severity", "Risk"]]

        # дочерние объекты у города по city.children
        for cid in city.children:
            n = next(node for node in nodes if node.id == cid)

            lower = (n.prob or 0.0) * (n.loss_min or 0.0)
            upper = (n.prob or 0.0) * (n.loss_max or 0.0)
            risk = (n.prob or 0.0) * (n.severity or 1.0)

            data.append([
                n.name,
                f"{n.prob:.3f}",
                f"{n.loss_min:.2f}",
                f"{n.loss_max:.2f}",
                f"{lower:.2f}",
                f"{upper:.2f}",
                f"{n.severity:.1f}",
                f"{risk:.2f}",
            ])

        table = Table(data, colWidths=[150, 40, 60, 60, 60, 60, 50, 50], repeatRows=1)
        table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), "Times-Roman"),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ]))

        elems.append(table)
        elems.append(Spacer(1, 12))

    doc.build(elems)
