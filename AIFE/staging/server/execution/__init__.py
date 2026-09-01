"""
Публичная поверхность execution authority.

[Purpose]
    Публичная поверхность execution authority.

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
    Claim,
    ClaimId,
    FencingToken,
    Lease,
    LeaseId,
    ReclaimResult,
    RenewalResult,
    StaleFencingAuthorityError,
    reclaim_lease,
    renew_lease,
    validate_terminal_authority,
)

__all__ = [
    "Claim",
    "ClaimId",
    "FencingToken",
    "Lease",
    "LeaseId",
    "ReclaimResult",
    "RenewalResult",
    "StaleFencingAuthorityError",
    "reclaim_lease",
    "renew_lease",
    "validate_terminal_authority",
]
