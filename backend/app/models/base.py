from sqlalchemy import inspect
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def loaded_relationship(obj, name: str):
    """Retorna o relacionamento somente se já estiver carregado (evita lazy-load em contexto assíncrono)."""
    state = inspect(obj)
    if name in state.unloaded:
        return None
    return getattr(obj, name)
