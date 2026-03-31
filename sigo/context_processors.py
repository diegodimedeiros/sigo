from .notifications import (
    modulo_contexto_notificacao,
    notificacoes_anotadas_para_request,
)


def notifications_context(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {
            "top_notifications": [],
            "top_notifications_unread_count": 0,
            "top_notifications_module": "",
        }

    modulo = modulo_contexto_notificacao(request, prefer_explicit=True)
    queryset = notificacoes_anotadas_para_request(request, prefer_explicit_module=True)

    top_notifications = list(queryset[:5])
    unread_count = queryset.filter(lida_por_usuario=False).count()

    return {
        "top_notifications": top_notifications,
        "top_notifications_unread_count": unread_count,
        "top_notifications_module": modulo,
    }
