from sigo_core.shared.normalizers import normalize_text
from sigo_core.shared.formatters import bool_ptbr as bool_label, fmt_dt

def parse_date_window(request):
    data_inicio = (request.POST.get("data_inicio") or request.GET.get("data_inicio") or "").strip()
    data_fim = (request.POST.get("data_fim") or request.GET.get("data_fim") or "").strip()
    return data_inicio, data_fim
