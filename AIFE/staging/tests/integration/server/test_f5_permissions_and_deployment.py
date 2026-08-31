"""Bounded F5 implementation acceptance tests for this mapped owner path."""

import json
import os

from server.configuration.models import F5ReadinessConfig
from server.runtime.readiness import evaluate_f5_readiness


def cfg(tmp_path, *, mapping=None, minimum_free_bytes=1):
    """Exercise the mapped F5 acceptance case."""
    root = tmp_path / "data"
    root.mkdir(exist_ok=True)
    mp = tmp_path / "deployment.json"
    d = {
        "control_schema_version": 1,
        "backing_identity": "disk-test",
        "data_root": str(root),
        "control_schema_id": "aife-server-control",
        "config_identity": "config-1",
        "active_release_identity": "release-1",
    }
    d.update(mapping or {})
    mp.write_text(json.dumps(d))
    return F5ReadinessConfig(
        deployment_map_path=mp,
        expected_release_identity="release-1",
        expected_config_identity="config-1",
        expected_backing_identity="disk-test",
        minimum_free_bytes=minimum_free_bytes,
    )


def test_f11_missing_data_root(tmp_path):
    """Exercise the mapped F5 acceptance case."""
    assert not evaluate_f5_readiness(
        cfg(tmp_path, mapping={"data_root": str(tmp_path / "missing")}),
        control_schema_check=lambda: None,
    ).ready


def test_f12_unwritable_data_root(tmp_path):
    """Exercise the mapped F5 acceptance case."""
    c = cfg(tmp_path)
    root = tmp_path / "data"
    os.chmod(root, 0o555)
    try:
        assert not evaluate_f5_readiness(c, control_schema_check=lambda: None).ready
    finally:
        os.chmod(root, 0o755)


def test_f13_insufficient_space(tmp_path):
    """Exercise the mapped F5 acceptance case."""
    assert not evaluate_f5_readiness(cfg(tmp_path, minimum_free_bytes=10**30), control_schema_check=lambda: None).ready


def test_f17_f18_deployment_release_config_schema_mismatch(tmp_path):
    """Exercise the mapped F5 acceptance case."""
    for m in (
        {"active_release_identity": "wrong"},
        {"config_identity": "wrong"},
        {"control_schema_id": "wrong"},
        {"control_schema_version": 2},
        {"backing_identity": "wrong"},
    ):
        assert not evaluate_f5_readiness(cfg(tmp_path, mapping=m), control_schema_check=lambda: None).ready
