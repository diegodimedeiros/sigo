import io

from django.contrib import messages
from django.shortcuts import redirect
from django.utils import timezone

from sigo_core.api import ApiStatus, api_error, api_success, is_json_request
from sigo_core.shared.formatters import user_display
from sigo_core.shared.pdf_export import build_numbered_canvas_class, draw_pdf_page_chrome, wrap_pdf_text_lines


def extract_error_details(exc):
    if hasattr(exc, "details") and exc.details:
        return exc.details
    if hasattr(exc, "message_dict"):
        return exc.message_dict
    return {"__all__": [str(exc)]}


def is_ajax_request(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def expects_form_api_response(request):
    return is_json_request(request) or is_ajax_request(request)


def form_success_response(*, request, instance, message, created=False):
    if expects_form_api_response(request):
        return api_success(
            data={"id": instance.id, "redirect_url": instance.get_absolute_url()},
            message=message,
            status=ApiStatus.CREATED if created else ApiStatus.OK,
        )
    messages.success(request, message)
    return redirect(instance.get_absolute_url())


def form_error_response(*, errors, message):
    return api_error(
        code="validation_error",
        message=message,
        status=ApiStatus.UNPROCESSABLE_ENTITY,
        details=errors,
    )


def build_record_pdf_context(request, *, report_title, report_subject, header_subtitle):
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

    dark_text = (0.15, 0.15, 0.15)
    page_content_top = height - 120
    min_y = 72
    info_x = 82

    def draw_page():
        draw_pdf_page_chrome(
            canvas=canvas,
            page_width=width,
            page_height=height,
            generated_by=user_display(request.user) or "Sistema",
            generated_at=timezone.localtime(timezone.now()),
            header_subtitle=header_subtitle,
        )

    draw_page()
    canvas.setFillColorRGB(*dark_text)
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawCentredString(width / 2, height - 140, report_title)

    return {
        "buffer": buffer,
        "canvas": canvas,
        "width": width,
        "height": height,
        "dark_text": dark_text,
        "page_content_top": page_content_top,
        "min_y": min_y,
        "info_x": info_x,
        "draw_page": draw_page,
    }


def draw_pdf_wrapped_section(canvas, *, title, text, x, y, width, min_y, page_content_top, draw_page, dark_text):
    title_y = y - 8
    if title_y < min_y:
        canvas.showPage()
        draw_page()
        title_y = page_content_top

    canvas.setFillColorRGB(*dark_text)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(x, title_y, title)

    lines = wrap_pdf_text_lines(text or "-", width - (x * 2))
    canvas.setFont("Helvetica", 10)
    next_y = title_y - 18
    for line in lines:
        if next_y < min_y:
            canvas.showPage()
            draw_page()
            canvas.setFillColorRGB(*dark_text)
            canvas.setFont("Helvetica-Bold", 11)
            canvas.drawString(x, page_content_top, f"{title} (continuação)")
            canvas.setFont("Helvetica", 10)
            next_y = page_content_top - 18
        canvas.drawString(x, next_y, line)
        next_y -= 13
    return next_y


def draw_pdf_list_section(canvas, *, title, items, x, y, min_y, page_content_top, draw_page, dark_text, empty_text):
    section_y = y - 12
    if section_y < min_y:
        canvas.showPage()
        draw_page()
        section_y = page_content_top

    canvas.setFillColorRGB(*dark_text)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(x, section_y, title)
    canvas.setFont("Helvetica", 9)

    next_y = section_y - 14
    if items:
        for index, item in enumerate(items, start=1):
            if next_y < min_y:
                canvas.showPage()
                draw_page()
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
