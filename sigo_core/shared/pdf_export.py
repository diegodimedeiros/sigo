import io
import os
from xml.sax.saxutils import escape

from django.conf import settings
from django.http import FileResponse, HttpResponse
from django.utils import timezone

from sigo_core.shared.formatters import to_export_text, user_display


def build_numbered_canvas_class(page_width):
    from reportlab.pdfgen import canvas as rl_canvas

    class NumberedCanvas(rl_canvas.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._saved_page_states = []

        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total_pages = len(self._saved_page_states)
            for state in self._saved_page_states:
                self.__dict__.update(state)
                self.setFillColorRGB(1, 1, 1)
                self.setFont("Helvetica", 8)
                self.drawRightString(page_width - 24, 6, f"{self._pageNumber} de {total_pages}")
                super().showPage()
            super().save()

    return NumberedCanvas


def draw_pdf_page_chrome(
    canvas,
    page_width,
    page_height,
    generated_by,
    generated_at=None,
    hash_cadastro=None,
    footer_suffix=None,
    footer_on_two_lines=False,
    header_subtitle=None,
):
    from reportlab.lib.utils import ImageReader

    generated_at = generated_at or timezone.localtime(timezone.now())

    green = (5 / 255, 150 / 255, 105 / 255)
    light_green = (52 / 255, 211 / 255, 153 / 255)
    dark_text = (0.15, 0.15, 0.15)

    canvas.setFillColorRGB(*green)
    canvas.rect(0, page_height - 92, page_width, 92, stroke=0, fill=1)

    path_top = canvas.beginPath()
    path_top.moveTo(0, page_height - 82)
    path_top.curveTo(page_width * 0.30, page_height - 70, page_width * 0.70, page_height - 94, page_width, page_height - 82)
    path_top.lineTo(page_width, page_height - 98)
    path_top.curveTo(page_width * 0.70, page_height - 110, page_width * 0.30, page_height - 86, 0, page_height - 98)
    path_top.close()
    canvas.setFillColorRGB(*light_green)
    canvas.drawPath(path_top, stroke=0, fill=1)

    title_y = page_height - 50
    logo_path = os.path.join(
        settings.BASE_DIR,
        "static",
        "sigo",
        "assets",
        "img",
        "institucional",
        "caracol_W.png",
    )

    if os.path.exists(logo_path):
        try:
            logo_img = ImageReader(logo_path)
            img_w, img_h = logo_img.getSize()
            max_w = 92
            max_h = 52
            scale = min(max_w / float(img_w), max_h / float(img_h))
            draw_w = img_w * scale
            draw_h = img_h * scale
            logo_y = title_y - (draw_h / 2.0)
            canvas.drawImage(
                logo_img,
                20,
                logo_y,
                width=draw_w,
                height=draw_h,
                mask="auto",
            )
        except Exception:
            pass

    canvas.setFillColorRGB(1, 1, 1)
    canvas.setFont("Helvetica-Bold", 14)
    canvas.drawCentredString(
        page_width / 2,
        title_y,
        "SIOP - Sistema de Inteligência e Operações",
    )
    if header_subtitle:
        canvas.setFont("Helvetica", 10)
        canvas.drawCentredString(page_width / 2, title_y - 16, header_subtitle)

    canvas.setFillColorRGB(*green)
    canvas.rect(0, 0, page_width, 42, stroke=0, fill=1)

    canvas.setFillColorRGB(*dark_text)
    canvas.setFont("Helvetica", 7)

    generated_text = f"Gerado em {generated_at.strftime('%d/%m/%Y %H:%M')} por {generated_by}"
    if footer_on_two_lines and hash_cadastro:
        hash_text = f"Hash Atendimento: {hash_cadastro}"
        if footer_suffix:
            hash_text = f"{hash_text} {footer_suffix}"
        canvas.drawRightString(page_width - 24, 62, generated_text)
        canvas.drawRightString(page_width - 24, 52, hash_text)
    else:
        if hash_cadastro:
            generated_text = f"{generated_text} | Hash Atendimento: {hash_cadastro}"
        if footer_suffix:
            generated_text = f"{generated_text} {footer_suffix}"
        canvas.drawRightString(page_width - 24, 56, generated_text)

    path_bottom = canvas.beginPath()
    path_bottom.moveTo(0, 47)
    path_bottom.curveTo(page_width * 0.28, 37, page_width * 0.72, 57, page_width, 47)
    path_bottom.lineTo(page_width, 31)
    path_bottom.curveTo(page_width * 0.72, 41, page_width * 0.28, 21, 0, 31)
    path_bottom.close()
    canvas.setFillColorRGB(*light_green)
    canvas.drawPath(path_bottom, stroke=0, fill=1)

    canvas.setFillColorRGB(1, 1, 1)
    canvas.setFont("Helvetica", 8.5)
    canvas.drawCentredString(
        page_width / 2,
        16,
        "Rodovia RS 466, km 0, s/n - Caracol, Canela - RS - CNPJ 48.255.552/0001-77",
    )


def draw_pdf_label_value(canvas, x, y, label, value, font_size=10):
    from reportlab.pdfbase.pdfmetrics import stringWidth

    label_txt = f"{label}: "
    canvas.setFont("Helvetica-Bold", font_size)
    canvas.drawString(x, y, label_txt)

    label_w = stringWidth(label_txt, "Helvetica-Bold", font_size)
    canvas.setFont("Helvetica", font_size)
    canvas.drawString(x + label_w, y, value or "-")


def wrap_pdf_text_lines(text, max_width, font_name="Helvetica", font_size=10):
    from reportlab.pdfbase.pdfmetrics import stringWidth

    text = (text or "").replace("\r", "")
    paragraphs = text.split("\n")
    wrapped = []

    for paragraph in paragraphs:
        words = paragraph.split()
        if not words:
            wrapped.append("")
            continue

        current = words[0]
        for word in words[1:]:
            tentative = f"{current} {word}"
            if stringWidth(tentative, font_name, font_size) <= max_width:
                current = tentative
            else:
                wrapped.append(current)
                current = word

        wrapped.append(current)

    return wrapped


def export_generic_pdf(
    request,
    queryset,
    *,
    filename_prefix,
    report_title,
    report_subject,
    headers,
    row_getters,
    base_col_widths,
    nowrap_indices=None,
    build_rows,
):
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A3, landscape
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError:
        return HttpResponse(
            "reportlab não está instalado. Execute: pip install reportlab",
            status=500,
        )

    now_local = timezone.localtime(timezone.now())
    filename = f"{filename_prefix}_{now_local.strftime('%Y%m%d_%H%M%S')}.pdf"
    nowrap_indices = set(nowrap_indices or [])

    green = colors.Color(5 / 255, 150 / 255, 105 / 255)
    light_green = colors.Color(225 / 255, 248 / 255, 238 / 255)
    dark_text = colors.Color(0.15, 0.15, 0.15)

    buffer = io.BytesIO()
    page_w, page_h = landscape(A3)
    NumberedCanvas = build_numbered_canvas_class(page_w)

    def add_page_chrome(canvas, doc):
        canvas.saveState()
        draw_pdf_page_chrome(
            canvas=canvas,
            page_width=page_w,
            page_height=page_h,
            generated_by=user_display(getattr(request, "user", None)) or "Sistema",
            generated_at=now_local,
        )
        canvas.restoreState()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A3),
        rightMargin=30,
        leftMargin=30,
        topMargin=110,
        bottomMargin=72,
        title=report_title,
        author=user_display(getattr(request, "user", None)) or "Sistema",
        subject=report_subject,
        creator="SIOP",
        producer="SIOP",
    )

    styles = getSampleStyleSheet()
    elements = [
        Paragraph(f"<para align='center'><b>{escape(report_title)}</b></para>", styles["h1"]),
        Spacer(1, 0.25 * 72),
    ]

    cell_style = styles["BodyText"].clone("table_body")
    cell_style.fontSize = 8
    cell_style.leading = 9

    data = [headers]

    for row in build_rows(queryset, row_getters):
        rendered_row = []
        for idx, value in enumerate(row):
            text = escape(to_export_text(value))
            if idx in nowrap_indices:
                text = text.replace(" ", "\u00A0")
            rendered_row.append(Paragraph(text, cell_style))
        data.append(rendered_row)

    total_base = float(sum(base_col_widths)) if base_col_widths else 0.0
    scale = (doc.width / total_base) if total_base else 1.0
    col_widths = [w * scale for w in base_col_widths]

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (-1, 0), green),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [light_green, colors.white]),
                ("TEXTCOLOR", (0, 1), (-1, -1), dark_text),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )

    elements.append(table)

    doc.build(
        elements,
        onFirstPage=add_page_chrome,
        onLaterPages=add_page_chrome,
        canvasmaker=NumberedCanvas,
    )

    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=filename)
