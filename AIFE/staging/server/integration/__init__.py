"""
Neutral domain-to-Server integration boundary.

[Purpose]
    Neutral domain-to-Server integration boundary.

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

from server.integration.bindings import (
    DomainAccessItem,
    DomainPublicationBinding,
    DomainReadbackMismatch,
    DomainRegistrationMismatch,
    DomainWorkBinding,
    DomainWriteMismatch,
    access_result_from_domain,
    bind_domain_publication,
    bind_domain_work,
    domain_input_identity,
    mark_canonically_registered,
    mark_durable_stored,
    mark_ingest_durable,
    mark_publishing,
    mark_readback_verified,
    mark_staged,
)
from server.integration.domain import (
    DomainArtifactEnvelope,
    DomainArtifactIdentity,
    DomainArtifactReferences,
    DomainArtifactTiming,
    DomainArtifactType,
)

__all__ = [
    "DomainAccessItem",
    "DomainArtifactEnvelope",
    "DomainArtifactIdentity",
    "DomainArtifactReferences",
    "DomainArtifactTiming",
    "DomainArtifactType",
    "DomainPublicationBinding",
    "DomainReadbackMismatch",
    "DomainRegistrationMismatch",
    "DomainWorkBinding",
    "DomainWriteMismatch",
    "access_result_from_domain",
    "bind_domain_publication",
    "bind_domain_work",
    "domain_input_identity",
    "mark_canonically_registered",
    "mark_durable_stored",
    "mark_ingest_durable",
    "mark_publishing",
    "mark_readback_verified",
    "mark_staged",
]
