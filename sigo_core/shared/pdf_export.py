
import io
import os
import logging
from xml.sax.saxutils import escape

from django.conf import settings
from django.http import FileResponse, HttpResponse
from django.utils import timezone

from sigo_core.shared.formatters import to_export_text, user_display


# =====================
# Constantes de Estilo/Layout
# =====================
PDF_COLORS = {
    "green": (5 / 255, 150 / 255, 105 / 255),
    "light_green": (52 / 255, 211 / 255, 153 / 255),
    "dark_text": (0.15, 0.15, 0.15),
}

PDF_LAYOUT = {
    "a4_content_x": 22.638,
    "a4_content_y": 80.454,
    "a4_content_width": 550.0,
    "a4_content_height": 650.0,
}

PDF_FONTS = {
    "header": ("Helvetica-Bold", 13),
    "subtitle": ("Helvetica", 11),
    "body": ("Helvetica", 10),
    "footer": ("Helvetica", 8.5),
    "label": ("Helvetica-Bold", 11),
    "list": ("Helvetica", 9),
}


# =====================
# Logger
# =====================
logger = logging.getLogger(__name__)



# =====================
# Helpers de Layout
# =====================
def get_a4_content_area():
    """Retorna o dicionário com a área útil do A4."""
    return {
        "x": PDF_LAYOUT["a4_content_x"],
        "y": PDF_LAYOUT["a4_content_y"],
        "width": PDF_LAYOUT["a4_content_width"],
        "height": PDF_LAYOUT["a4_content_height"],
        "right": PDF_LAYOUT["a4_content_x"] + PDF_LAYOUT["a4_content_width"],
        "top": PDF_LAYOUT["a4_content_y"] + PDF_LAYOUT["a4_content_height"],
    }

# --- Helper de quebra de página ---

def ensure_space(canvas, y, min_y, page_content_top, draw_page):
    """Garante espaço na página, faz quebra se necessário."""
    if y < min_y:
        canvas.showPage()
        draw_page()
        return page_content_top
    return y

# --- Helper seguro para imagens ---

def safe_draw_image(canvas, path, *args, **kwargs):
    """Desenha imagem de forma segura, logando erros."""
    if not os.path.exists(path):
        return False
    try:
        canvas.drawImage(path, *args, **kwargs)
        return True
    except Exception:
        logger.exception("Erro ao desenhar imagem no PDF: %s", path)
        return False


#############################
# Canvas e Chrome Visual
#############################
def build_numbered_canvas_class(page_width):
    """Classe canvas que adiciona numeração de páginas."""
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
    header_subtitle=None,
):
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfbase.pdfmetrics import stringWidth

    green = PDF_COLORS["green"]
    light_green = PDF_COLORS["light_green"]

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
        "sigo",
        "sigo.png",
    )

    if os.path.exists(logo_path):
        try:
            logo_img = ImageReader(logo_path)
            img_w, img_h = logo_img.getSize()
            max_w = 84
            max_h = 44
            scale = min(max_w / float(img_w), max_h / float(img_h))
            draw_w = img_w * scale
            draw_h = img_h * scale
            # Ajuste: subir o logo 12 pontos a mais
            logo_y = title_y - (draw_h / 2.0) + 12
            canvas.drawImage(
                logo_img,
                20,
                logo_y,
                width=draw_w,
                height=draw_h,
                mask="auto",
            )
        except Exception:
            logger.exception("Erro ao desenhar imagem no PDF: %s", logo_path)

    # --- Cabeçalho limpo e objetivo ---
    font_name, font_size = PDF_FONTS["header"]
    canvas.setFont(font_name, font_size)
    canvas.setFillColorRGB(1, 1, 1)  # Branco
    canvas.drawCentredString(page_width / 2, title_y, "Sistema Integrado de Gestão Operacional")

    if header_subtitle:
        font_name, font_size = PDF_FONTS["subtitle"]
        canvas.setFont(font_name, font_size)
        canvas.setFillColorRGB(1, 1, 1)  # Branco
        canvas.drawCentredString(page_width / 2, title_y - 18, header_subtitle)

    # Aumentar altura do rodapé
    rodape_altura = 52
    curva_y1 = 57 
    curva_y2 = 47
    curva_y3 = 67
    curva_y4 = 39
    curva_y5 = 49
    curva_y6 = 29

    canvas.setFillColorRGB(*green)
    canvas.rect(0, 0, page_width, rodape_altura, stroke=0, fill=1)

    path_bottom = canvas.beginPath()
    path_bottom.moveTo(0, curva_y1)
    path_bottom.curveTo(page_width * 0.28, curva_y2, page_width * 0.72, curva_y3, page_width, curva_y1)
    path_bottom.lineTo(page_width, curva_y4)
    path_bottom.curveTo(page_width * 0.72, curva_y5, page_width * 0.28, curva_y6, 0, curva_y4)
    path_bottom.close()
    canvas.setFillColorRGB(*light_green)
    canvas.drawPath(path_bottom, stroke=0, fill=1)

    canvas.setFillColorRGB(1, 1, 1)
    canvas.setFont("Helvetica", 8.5)
    footer_text = "Rodovia RS 466, km 0, s/n - Caracol, Canela - RS - CNPJ 48.255.552/0001-77"
    footer_y = 18  # era 10, subiu 8 pontos
    footer_font = "Helvetica"
    footer_font_size = 8.5
    logo_footer_path = os.path.join(
        settings.BASE_DIR,
        "static",
        "sigo",
        "assets",
        "img",
        "institucional",
        "parque_caracol_white.png",
    )
    logo_gap = 8
    logo_w = 64
    logo_h = 64
    text_w = stringWidth(footer_text, footer_font, footer_font_size)
    total_w = text_w
    logo_drawn = False

    if os.path.exists(logo_footer_path):
        try:
            footer_logo = ImageReader(logo_footer_path)
            img_w, img_h = footer_logo.getSize()
            scale = min(logo_w / float(img_w), logo_h / float(img_h))
            draw_w = img_w * scale
            draw_h = img_h * scale
            total_w += draw_w + logo_gap
            start_x = (page_width - total_w) / 2
            canvas.drawImage(
                footer_logo,
                start_x,
                footer_y - ((draw_h - footer_font_size) / 2.0),
                width=draw_w,
                height=draw_h,
                mask="auto",
            )
            canvas.drawString(start_x + draw_w + logo_gap, footer_y, footer_text)
            logo_drawn = True
        except Exception:
            logger.exception("Erro ao desenhar imagem no PDF: %s", logo_footer_path)

    if not logo_drawn:
        canvas.drawCentredString(page_width / 2, footer_y, footer_text)


#############################
# Helpers de Texto e Layout
#############################
def draw_pdf_label_value(canvas, x, y, label, value, font_size=10):
    """Desenha um label e valor na mesma linha."""
    from reportlab.pdfbase.pdfmetrics import stringWidth

    label_txt = f"{label}: "
    canvas.setFont("Helvetica-Bold", font_size)
    canvas.drawString(x, y, label_txt)

    label_w = stringWidth(label_txt, "Helvetica-Bold", font_size)
    canvas.setFont("Helvetica", font_size)
    canvas.drawString(x + label_w, y, value or "-")


def wrap_pdf_text_lines(text, max_width, font_name="Helvetica", font_size=10):
    """Quebra texto em múltiplas linhas para caber no PDF."""
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


#############################
# Exportação de Tabela PDF
#############################
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


#############################
# Contexto para PDF de Registro Individual
#############################
def build_record_pdf_context(request, *, report_title, report_subject, header_subtitle):
    """Inicializa um canvas ReportLab para PDFs de registro individual (view-PDF).

    Retorna um dicionário com todos os objetos necessários para desenhar o PDF
    campo a campo usando draw_pdf_label_value, draw_pdf_wrapped_section e
    draw_pdf_list_section. Retorna None se reportlab não estiver instalado.

    Uso:
        ctx = build_record_pdf_context(request, report_title=..., ...)
        if ctx is None:
            return HttpResponse("reportlab ausente", status=500)
        canvas, buffer = ctx["canvas"], ctx["buffer"]
    """
    try:
        from reportlab.lib.pagesizes import A4
    except ImportError:
        return None

    width, height = A4
    buffer = io.BytesIO()
    numbered_canvas = build_numbered_canvas_class(width)
    canvas = numbered_canvas(buffer, pagesize=A4)
    canvas.setTitle(report_title)
    canvas.setAuthor(user_display(request.user))
    canvas.setSubject(report_subject)

    content_area = get_a4_content_area()
    dark_text = (0.15, 0.15, 0.15)
    page_content_top = content_area["top"]
    min_y = content_area["y"]
    info_x = content_area["x"]

    def draw_page():
        draw_pdf_page_chrome(
            canvas=canvas,
            page_width=width,
            page_height=height,
            header_subtitle=header_subtitle,
        )

    draw_page()
    canvas.setFillColorRGB(*dark_text)
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawCentredString(width / 2, content_area["top"] - 60, report_title)

    return {
        "buffer": buffer,
        "canvas": canvas,
        "width": width,
        "height": height,
        "content_area": content_area,
        "dark_text": dark_text,
        "page_content_top": page_content_top,
        "min_y": min_y,
        "info_x": info_x,
        "draw_page": draw_page,
    }


def draw_pdf_wrapped_section(canvas, *, title, text, x, y, width, min_y, page_content_top, draw_page, dark_text):
    """Desenha seção de texto longo com quebra automática e paginação."""
    """Desenha uma seção de texto longo com quebra automática de linha e paginação.

    Cuida da mudança de página quando o conteúdo ultrapassar min_y.
    Retorna a posição y final após o texto.
    """
    title_y = y - 8
    title_y = ensure_space(canvas, title_y, min_y, page_content_top, draw_page)

    canvas.setFillColorRGB(*dark_text)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(x, title_y, title)

    lines = wrap_pdf_text_lines(text or "-", width - (x * 2))
    canvas.setFont("Helvetica", 10)
    next_y = title_y - 18
    for line in lines:
        next_y = ensure_space(canvas, next_y, min_y, page_content_top, draw_page)
        if next_y == page_content_top:
            canvas.setFillColorRGB(*dark_text)
            canvas.setFont("Helvetica-Bold", 11)
            canvas.drawString(x, page_content_top, f"{title} (continuação)")
            canvas.setFont("Helvetica", 10)
            next_y = page_content_top - 18
        canvas.drawString(x, next_y, line)
        next_y -= 13
    return next_y


def draw_pdf_list_section(canvas, *, title, items, x, y, min_y, page_content_top, draw_page, dark_text, empty_text):
    """Desenha seção de lista numerada com paginação automática."""
    """Desenha uma seção de lista numerada com paginação automática.

    Se items for vazio, exibe empty_text.
    Retorna a posição y final após a lista.
    """
    section_y = y - 12
    section_y = ensure_space(canvas, section_y, min_y, page_content_top, draw_page)

    canvas.setFillColorRGB(*dark_text)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(x, section_y, title)
    canvas.setFont("Helvetica", 9)

    next_y = section_y - 14
    if items:
        for index, item in enumerate(items, start=1):
            next_y = ensure_space(canvas, next_y, min_y, page_content_top, draw_page)
            if next_y == page_content_top:
                canvas.setFillColorRGB(*dark_text)
                canvas.setFont("Helvetica-Bold", 11)
                canvas.drawString(x, page_content_top, f"{title} (continuação)")
                canvas.setFont("Helvetica", 9)
                next_y = page_content_top - 14
            canvas.drawString(x + 4, next_y, f"{index}. {item}")
            next_y -= 12
    else:
        canvas.drawString(x + 4, next_y, empty_text)
    return next_y
