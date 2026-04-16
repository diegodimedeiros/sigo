import csv

from django.http import HttpResponse
from django.utils.http import content_disposition_header
from django.utils import timezone

from sigo_core.shared.formatters import to_export_text
from sigo_core.shared.helpers import build_rows


def export_generic_csv(request, queryset, *, filename_prefix, headers, row_getters):
    now_local = timezone.localtime(timezone.now())
    filename = f"{filename_prefix}_{now_local.strftime('%Y%m%d_%H%M%S')}.csv"

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = content_disposition_header(
        as_attachment=True,
        filename=filename,
    )
    response.write("\ufeff")

    writer = csv.writer(response, delimiter=";")
    writer.writerow(headers)

    for row in build_rows(queryset, row_getters):
        writer.writerow([to_export_text(v) for v in row])

    return response