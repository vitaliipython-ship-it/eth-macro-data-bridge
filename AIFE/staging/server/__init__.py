"""Публичная корневая поверхность Server/Data F3.

Пакет публикует только типизированную composition boundary и process-role identity;
доменная семантика и конкретные backend остаются за пределами F3.
"""

from server.configuration import ProcessRole
from server.runtime import ServerRuntimeDependencies

__all__ = ["ProcessRole", "ServerRuntimeDependencies"]
