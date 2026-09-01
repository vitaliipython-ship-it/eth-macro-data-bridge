"""
Bounded F5 implementation acceptance tests for this mapped owner path.

[Purpose]
    Доказать bounded F5 implementation acceptance tests for this mapped owner path.

[Description]
    Модуль ограничен текущим F5/C-144 contour и сохраняет существующие owner boundaries.
    Он не создаёт вторую semantic authority и не выполняет production activation.

[Components]
    - Pytest cases и fixtures, проверяющие mapped F5 invariants этого owner path.

[Usage]
    Запускать через canonical pytest/toolchain gates; тесты не являются production runtime.

[Architecture]
    Test surface проверяет generic AIFE Server contour на disposable future-AIFE tree; Data Bridge
    остаётся authority domain semantics.

[Note]
    Physical SQLite/filesystem и Docker qualification имеют отдельные evidence gates поверх этих тестов.

[Warning]
    Не ослаблять assertions и не принимать unit/integration PASS за production или Docker activation.
"""

import json

from server.configuration.models import F5ReadinessConfig
from server.runtime.readiness import (
    ControlBackendCorrupt,
    ControlBackendUnavailable,
    ControlSchemaIncompatible,
    evaluate_f5_readiness,
)


def make_cfg(tmp_path, *, mapping=None, minimum_free_bytes=1):
    """Exercise the mapped F5 acceptance case."""
    root = tmp_path / "data"
    root.mkdir(exist_ok=True)
    mp = tmp_path / "deployment.json"
    data = {
        "active_release_identity": "release-1",
        "config_identity": "config-1",
        "control_schema_id": "aife-server-control",
        "control_schema_version": 1,
        "data_root": str(root),
        "backing_identity": "disk-test",
    }
    data.update(mapping or {})
    mp.write_text(json.dumps(data))
    return F5ReadinessConfig(
        mp,
        "release-1",
        "config-1",
        minimum_free_bytes=minimum_free_bytes,
        expected_backing_identity="disk-test",
    )


def test_readiness_predicates_pass_only_in_isolated_fixture(tmp_path):
    """Probe uses the F5 storage seam and cleans only its dedicated namespace."""
    config = make_cfg(tmp_path)
    root = tmp_path / "data"
    sentinel = root / "do-not-delete"
    sentinel.write_bytes(b"unrelated")

    report = evaluate_f5_readiness(config, control_schema_check=lambda: None)

    assert report.ready
    assert any(check.name == "durable_write_readback_probe" and check.passed for check in report.checks)
    assert any(check.name == "readiness_probe_cleanup_bounded" and check.passed for check in report.checks)
    assert sentinel.read_bytes() == b"unrelated"
    assert not (root / ".aife-readiness").exists()
    assert not (root / "objects").exists()


def test_f14_f15_f16_control_failures_fail_closed(tmp_path):
    """Exercise the mapped F5 acceptance case."""
    for error in (
        ControlBackendUnavailable,
        ControlSchemaIncompatible,
        ControlBackendCorrupt,
    ):

        def fail(error=error):
            """Exercise the mapped F5 acceptance case."""
            raise error("x")

        assert not evaluate_f5_readiness(make_cfg(tmp_path), control_schema_check=fail).ready
