"""Проверки runtime/application composition boundary F3."""

import ast
from datetime import timedelta
from pathlib import Path

from server.configuration import LeaseTimingConfig, ProcessRole, RetryTimingConfig


def test_process_roles_are_defined_without_orchestration() -> None:
    """Проверить типы ролей без запуска оркестрации."""
    assert {role.value for role in ProcessRole} == {"CONTROL", "WORKER", "COMBINED_INITIAL_NODE"}
    lease = LeaseTimingConfig(timedelta(minutes=5), timedelta(minutes=1))
    retry = RetryTimingConfig(timedelta(seconds=1), timedelta(seconds=10))
    assert lease.default_lease == timedelta(minutes=5)
    assert retry.delay_for(5) == timedelta(seconds=10)


def test_server_package_has_no_global_runtime_singleton() -> None:
    """Проверить отсутствие глобального runtime singleton."""
    server_root = Path(__file__).resolve().parents[3] / "server"
    for path in server_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.Assign):
                names = [target.id for target in node.targets if isinstance(target, ast.Name)]
                assert not any(name in {"runtime", "server_runtime", "service_locator"} for name in names)
