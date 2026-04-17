from __future__ import annotations

from django.contrib.auth import get_user_model

User = get_user_model()

GROUP_SIOP = "group_siop"
GROUP_SESMT = "group_sesmt"
GROUP_REPORTOS = "group_reportos"


def user_group_names(user: User) -> set[str]:
    if not user or not getattr(user, "is_authenticated", False):
        return set()
    return set(user.groups.values_list("name", flat=True))


def can_access_namespace(user: User, namespace: str) -> bool:
    if not namespace:
        return True

    if not user or not getattr(user, "is_authenticated", False):
        return False

    if user.is_superuser:
        return True

    # Access policy is active only for SIOP and SESMT at this stage.
    groups = user_group_names(user)
    has_siop = GROUP_SIOP in groups
    has_sesmt = GROUP_SESMT in groups

    if namespace == "siop":
        return has_siop
    if namespace == "sesmt":
        return has_sesmt

    # Keep other namespaces unrestricted for now.
    return True


def post_login_route_name(user: User) -> str:
    if not user or not getattr(user, "is_authenticated", False):
        return "sigo:login"

    if user.is_superuser:
        return "sigo:home"

    groups = user_group_names(user)

    has_siop = GROUP_SIOP in groups
    has_sesmt = GROUP_SESMT in groups
    has_reportos = GROUP_REPORTOS in groups

    if has_siop:
        return "siop:home"
    if has_sesmt:
        return "sesmt:home"
    if has_reportos:
        return "reportos:home"
    return "sigo:home"


def allowed_notification_modules(user: User) -> set[str]:
    base = {"", "sigo"}

    if not user or not getattr(user, "is_authenticated", False):
        return {""}

    if user.is_superuser:
        return {"", "sigo", "siop", "sesmt"}

    groups = user_group_names(user)
    allowed = set(base)

    if GROUP_SIOP in groups:
        allowed.add("siop")
    if GROUP_SESMT in groups:
        allowed.add("sesmt")

    # If user has no SIOP/SESMT group yet, keep legacy behavior.
    if allowed == base:
        return {"", "sigo", "siop", "sesmt"}
    return allowed
