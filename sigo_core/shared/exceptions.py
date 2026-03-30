from dataclasses import dataclass

from sigo_core.api import ApiStatus


@dataclass
class ServiceError(Exception):
    code: str
    message: str
    status: int = ApiStatus.UNPROCESSABLE_ENTITY
    details: dict | None = None