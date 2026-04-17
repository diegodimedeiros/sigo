from django.shortcuts import render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from .access import can_access_namespace


class ModuleAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return None

        resolver_match = getattr(request, "resolver_match", None)
        namespace = getattr(resolver_match, "namespace", "") if resolver_match else ""
        if not namespace:
            return None

        if can_access_namespace(user, namespace):
            return None

        referer = request.META.get("HTTP_REFERER", "")
        if referer and url_has_allowed_host_and_scheme(
            url=referer,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            back_url = referer
        else:
            back_url = reverse("sigo:home")

        return render(
            request,
            "sigo/module_access_denied.html",
            {
                "blocked_module": namespace.upper() if namespace else "MÓDULO",
                "back_url": back_url,
            },
            status=403,
        )
