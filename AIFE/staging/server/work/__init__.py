"""
Публичная поверхность модели работы.

[Purpose]
    Публичная поверхность модели работы.

[Description]
    Модуль ограничен текущим F5/C-144 contour и сохраняет существующие owner boundaries.
    Он не создаёт вторую semantic authority и не выполняет production activation.

[Components]
    - Типизированные компоненты bounded F5 contour, определённые этим модулем.

[Usage]
    Импортировать только явно экспортированные generic Server компоненты; package root не владеет lifecycle сам по себе.

[Architecture]
    Package участвует в generic AIFE Server contour; market-data/provider semantics остаются в ETH Macro Data Bridge.

[Note]
    Модуль не активирует F5M, production, Docker или real canonical AIFE integration.

[Warning]
    Не добавлять сюда domain resolver, второй scheduler, persistence framework или provider semantics.
"""

from .models import (
    AttemptId,
    IdempotencyIdentity,
    InvalidWorkTransition,
    ProvenanceReference,
    TerminalResultReference,
    WorkExecutionStatus,
    WorkId,
    WorkIdentityReferences,
    WorkRecord,
    WorkRetryIdentity,
    WorkState,
    WorkType,
    retry_identity,
    transition_work,
)

__all__ = [
    "AttemptId",
    "IdempotencyIdentity",
    "InvalidWorkTransition",
    "ProvenanceReference",
    "TerminalResultReference",
    "WorkExecutionStatus",
    "WorkId",
    "WorkIdentityReferences",
    "WorkRecord",
    "WorkRetryIdentity",
    "WorkState",
    "WorkType",
    "retry_identity",
    "transition_work",
]
