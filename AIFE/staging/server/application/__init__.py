"""
Публичная application boundary Server/Data.

[Purpose]
    Определить публичную application boundary bounded Server/Data contour.

[Description]
    Модуль ограничен текущим F5/C-144 contour и сохраняет существующие owner boundaries.
    Он не создаёт вторую semantic authority и не выполняет production activation.

[Components]
    - Экспорт application service surface без собственного durable state.

[Usage]
    Импортировать только явно экспортированные generic Server компоненты; package root не владеет lifecycle сам по себе.

[Architecture]
    Package участвует в generic AIFE Server contour; market-data/provider semantics остаются в ETH Macro Data Bridge.

[Note]
    Модуль не активирует F5M, production, Docker или real canonical AIFE integration.

[Warning]
    Не добавлять сюда domain resolver, второй scheduler, persistence framework или provider semantics.
"""

from .services import (
    AccessService,
    ExecutionService,
    PublicationService,
    SchedulingService,
    ServerApplicationServices,
    WorkService,
)

__all__ = [
    "AccessService",
    "ExecutionService",
    "PublicationService",
    "SchedulingService",
    "ServerApplicationServices",
    "WorkService",
]
