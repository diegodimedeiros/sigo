def anexos_total(item):
    total = getattr(item, "total_anexos", None)
    if total is not None:
        return total

    anexos = getattr(item, "anexos", None)
    if anexos is not None and hasattr(anexos, "count"):
        try:
            return anexos.count()
        except Exception:
            return 0

    return 0


def first_geolocalizacao_text(item):
    geos = getattr(item, "geolocalizacoes", None)
    if geos is None or not hasattr(geos, "first"):
        return ""

    geo = geos.first()
    if not geo:
        return ""

    return f"{geo.latitude}, {geo.longitude}"


def assinatura_status(item):
    assinaturas = getattr(item, "assinaturas", None)
    if assinaturas is None or not hasattr(assinaturas, "exists"):
        return ""

    return "Capturada" if assinaturas.exists() else "Não"


def build_rows(queryset, row_getters):
    rows = []
    for item in queryset:
        row = []
        for getter in row_getters:
            value = getter(item) if callable(getter) else getattr(item, getter, "")
            row.append(value)
        rows.append(row)
    return rows