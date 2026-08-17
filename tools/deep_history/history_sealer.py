from __future__ import annotations

from pathlib import Path
from typing import Any

import _history_sealer_core as _core
from revision_materializer import apply_kraken_revision_evidence

# Public compatibility facade: retain the existing D9.3 sealer interface while the
# PIT revision overlay is applied at the generation-membership boundary. The core
# module is the byte-preserved predecessor implementation, not a second sealer route.
for _name, _value in vars(_core).items():
    if not _name.startswith("__"):
        globals()[_name] = _value

_original_generation_membership_states = _core.generation_membership_states


def generation_membership_states(as_of_ms: int, root: Path = ROOT) -> list[dict[str, Any]]:
    states = _original_generation_membership_states(as_of_ms, root)
    authority_by_series = {
        item["series_id"]: item for item in _core.declared_regular_authority(root).values()
    }
    for state in states:
        for member in state.get("members", []):
            semantic = authority_by_series.get(member.get("series_id"))
            if semantic is None:
                raise RuntimeError(f"declared sealer authority missing during PIT materialization: {member.get('series_id')}")
            rows, resources = apply_kraken_revision_evidence(
                semantic,
                member["rows"],
                member["resources"],
                start_ms=member["start_ms"],
                end_ms=member["end_ms"],
                as_of_ms=as_of_ms,
                root=root,
            )
            gaps = _core._validate_fixed_grid(
                rows,
                member["start_ms"],
                member["end_ms"],
                semantic["step_ms"],
                semantic["coverage_start_ms"],
            )
            if gaps:
                raise RuntimeError(f"PIT revision materialization changed fixed-grid membership: {member['series_id']}")
            member["rows"] = rows
            member["resources"] = resources
    return states


# All existing build/detect/publish functions resolve this global from the core
# module. Patch that single semantic seam so direct imports and the CLI share the
# same implementation and source authority.
_core.generation_membership_states = generation_membership_states
globals()["generation_membership_states"] = generation_membership_states


if __name__ == "__main__":
    _core.main()
