def sidebar_permissions(request):
    user = getattr(request, "user", None)
    show_settings = bool(
        user
        and getattr(user, "is_authenticated", False)
        and (
            getattr(user, "is_superuser", False)
            or getattr(user, "is_staff", False)
            or user.groups.filter(name__iexact="administrador").exists()
        )
    )
    return {"show_settings": show_settings}
