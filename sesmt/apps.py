from django.apps import AppConfig


class SesmtConfig(AppConfig):
    name = 'sesmt'

    def ready(self):
        from . import sesmt_to_siop_sync  # noqa: F401
