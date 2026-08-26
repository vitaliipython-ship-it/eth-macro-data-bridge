---
title: "Тестовый и проверочный слой"
id: DOC-10-ARCHITECTURE-TREE-TOOLING-TESTS-VERIFICATION
version: '0.5'
status: active
owner: Architecture Lead
created: 2026-06-04
updated: 2026-08-05
review_cycle_days: 90
next_review_due: 2026-09-21
tags: [architecture, tree]
category: architecture
doc_type: design
language: ru
authority_reference:
  - ../../architecture.md
---

# Тестовый и проверочный слой

## Назначение

Дерево покрывает `tests/` как слой доказательства: unit, integration, performance, smoke и helpers.

## Дерево

```text
tests/  # Тестовый и проверочный слой проекта.
├── helpers/  # Общие помощники тестового слоя.
│   ├── __init__.py  # Инициализация Python-пакета `helpers`.
│   ├── file_helpers.py  # Python-модуль: Набор небольших файловых утилит, используемых в тестах..
│   ├── leakage_observability.py  # Python-модуль: Предоставить bounded observability probes для residue/leakage проверок в тестах..
│   ├── main_helpers.py  # Python-модуль: Общие тестовые заглушки и хелперы для тестов `main`..
│   └── rollback_utils.py  # Python-модуль: Утилиты для проверки поведения отката (rollback) при ошибочной инициализации..
├── integration/  # Интеграционные проверки связей между слоями.
│   ├── server/  # Cross-contract proof F3 без ETH/backend integration.
│   │   └── test_contract_flow.py  # WORK→SCHEDULING→EXECUTION→PUBLICATION→STORAGE→ACCESS и no-ETH boundary.
│   ├── scripts/  # Интеграционные доказательства инструментального runtime.
│   │   ├── patch_workspace/  # Фактический Windows long-path и Git materialization proof.
│   │   │   ├── __init__.py  # Граница integration-пакета общего path runtime.
│   │   │   └── test_windows_long_paths.py  # Реальные create/write/read/rename/delete, clone и worktree длиннее 260.
│   │   ├── test_archive_only_quality_linux.py  # Физическая Linux archive-only проверка verified carrier.
│   │   ├── test_archive_only_quality_windows.py  # Физическая Windows build-host проверка Linux target carrier.
│   │   └── test_review_package_materialization.py  # Интеграция run-scoped bytes, latest и finalization identity.
│   ├── ui/  # Интерфейс, рабочая область, панели, графики и визуальные компоненты.
│   │   ├── actions/  # Каталог actions; назначение уточняется по дочерним файлам.
│   │   │   └── test_action_descriptor_runtime_integration.py  # Python-модуль: Проверка runtime wiring unified ActionDescriptor (C-072) в реальном UI flow..
│   │   ├── chart/  # Каталог chart; назначение уточняется по дочерним файлам.
│   │   │   └── test_chart_layout_mode_integration.py  # Python-модуль: Integration-тесты runtime wiring layout mode: MainWindow -> ChartTabManager -> ChartWidget (C-071)..
│   │   ├── main_window/  # Каталог main window; назначение уточняется по дочерним файлам.
│   │   │   └── test_main_window_data_panel_integration.py  # Python-модуль: Integration-тесты для связки MainWindow ↔ MarketOverview ↔ DataPanel (C-050)..
│   │   ├── window_chrome/  # Каталог window chrome; назначение уточняется по дочерним файлам.
│   │   │   ├── test_menu_toolbar_window_controls_flow.py  # Python-модуль: Integration smoke-тесты для C-067: MenuBar parity, window controls states, toolbar QToolButton selectors..
│   │   │   └── test_toolbar_docking_flow.py  # Python-модуль: Integration tests for toolbar docking/redocking/reorder/restore flow (C-067)..
│   │   ├── workspace/  # Каталог workspace; назначение уточняется по дочерним файлам.
│   │   │   ├── drag_drop/  # Каталог drag drop; назначение уточняется по дочерним файлам.
│   │   │   │   ├── helpers/  # Общие помощники тестового слоя.
│   │   │   │   │   ├── __init__.py  # Инициализация Python-пакета `helpers`.
│   │   │   │   │   ├── _common_runtime_helpers.py  # Python-модуль: Сгруппировать residual assertion/debug helpers общего drag/drop runtime contour..
│   │   │   │   │   ├── _control_runtime_helpers.py  # Python-модуль: Сгруппировать helpers для catalog и geometry drag/drop controls..
│   │   │   │   │   ├── _gesture_runtime_helpers.py  # Python-модуль: Модуль предоставляет helper-функции для gesture и apply-путей integration drag/drop тестов..
│   │   │   │   │   ├── _layout_runtime_helpers.py  # Python-модуль: Сгруппировать geometry/layout helpers для runtime drag/drop tests..
│   │   │   │   │   ├── _observability_runtime_helpers.py  # Python-модуль: Собрать pilot-specific observability helpers для `D-125` drag/drop contour..
│   │   │   │   │   ├── _reset_checker.py  # Python-модуль: Предоставить единый reset/metadata checker для bounded drag/drop test contour..
│   │   │   │   │   ├── _settle_runtime_helpers.py  # Python-модуль: Сгруппировать drain/settle helpers для runtime drag/drop tests..
│   │   │   │   │   ├── _shared_main_window_runtime.py  # Python-модуль: Предоставить reusable `MainWindow` controller для module-scoped bootstrap reuse.
│   │   │   │   │   └── _window_runtime_helpers.py  # Python-модуль: Сгруппировать window/session/runtime widget helpers для drag/drop tests..
│   │   │   │   ├── interaction/  # Каталог interaction; назначение уточняется по дочерним файлам.
│   │   │   │   │   ├── __init__.py  # Инициализация Python-пакета `interaction`.
│   │   │   │   │   ├── test_gesture_transfer_runtime.py  # Python-модуль: Проверять gesture и transfer runtime contracts drag/drop..
│   │   │   │   │   ├── test_hover_control_runtime.py  # Python-модуль: Проверять hover/control runtime contracts drag/drop..
│   │   │   │   │   └── test_local_commit_runtime.py  # Python-модуль: Модуль проверяет local preview/commit runtime-сценарии drag/drop внутри workspace..
│   │   │   │   ├── local_anchor/  # Каталог local anchor; назначение уточняется по дочерним файлам.
│   │   │   │   │   ├── __init__.py  # Инициализация Python-пакета `local_anchor`.
│   │   │   │   │   ├── _shared.py  # Python-модуль: Общие helper-функции для bounded local-anchor runtime tests..
│   │   │   │   │   ├── test_local_anchor_handoff_owner_runtime.py  # Python-модуль: Runtime proofs для handoff owner contracts local-anchor между соседними.
│   │   │   │   │   ├── test_local_anchor_slot_solver_runtime.py  # Python-модуль: Runtime proofs для slot-solver и overlay geometry local-anchor.
│   │   │   │   │   ├── test_local_anchor_stability_runtime.py  # Python-модуль: Проверять stability runtime contracts для local anchor drag/drop..
│   │   │   │   │   └── test_local_anchor_surface_routes_runtime.py  # Python-модуль: Runtime proofs для local-anchor routes на hovered panel.
│   │   │   │   ├── main_local/  # Каталог main local; назначение уточняется по дочерним файлам.
│   │   │   │   │   ├── __init__.py  # Инициализация Python-пакета `main_local`.
│   │   │   │   │   ├── conftest.py  # Python-модуль: Материализовать module-scoped shared `MainWindow` fixture для `main_local` contour..
│   │   │   │   │   ├── test_main_local_regression_runtime.py  # Python-модуль: Проверять main-local regression runtime contracts drag/drop..
│   │   │   │   │   ├── test_main_repeated_sequence_runtime.py  # Python-модуль: Проверять repeated sequence runtime contracts для main-local drag/drop..
│   │   │   │   │   ├── test_main_ring_topology_runtime.py  # Python-модуль: Модуль проверяет runtime-контракты ring topology для `MAIN_*` зон workspace drag/drop..
│   │   │   │   │   └── test_main_surface_runtime.py  # Python-модуль: Проверять main-surface runtime contracts drag/drop..
│   │   │   │   ├── validation/  # Каталог validation; назначение уточняется по дочерним файлам.
│   │   │   │   │   ├── settle/  # Каталог settle; назначение уточняется по дочерним файлам.
│   │   │   │   │   │   ├── __init__.py  # Инициализация Python-пакета `settle`.
│   │   │   │   │   │   ├── _condition_based_settle_rollout_runtime.py  # Python-модуль: Materialize-ить bounded D-135 rollout confirmation для condition-based settle API..
│   │   │   │   │   │   ├── _condition_based_settle_runtime.py  # Python-модуль: Materialize-ить bounded D-130 condition-based settle validation contour..
│   │   │   │   │   │   ├── test_condition_based_settle_rollout_runtime.py  # Python-модуль: Проверить bounded D-135 rollout closure для condition-based settle API..
│   │   │   │   │   │   └── test_condition_based_settle_runtime.py  # Python-модуль: Проверить D-130 condition-based settle validation contour на named drag/drop pilot..
│   │   │   │   │   ├── __init__.py  # Инициализация Python-пакета `validation`.
│   │   │   │   │   ├── _main_window_validation_models.py  # Python-модуль: Содержать shared constants и evidence models для D-129 validation contour..
│   │   │   │   │   ├── _main_window_validation_runtime.py  # Python-модуль: Сформировать D-129 валидационный контур для `MainWindow`, переиспользуемого в рамках одной сессии..
│   │   │   │   │   ├── _random_order_validation_runtime.py  # Python-модуль: Materialize-ить bounded D-126 random-order / repeated-run validation contour..
│   │   │   │   │   ├── conftest.py  # Python-модуль: Предоставить opt-in фикстуру для D-129 session-bounded `MainWindow` prototype..
│   │   │   │   │   ├── test_main_window_validation_runtime.py  # Python-модуль: Проверить D-129 session-bounded `MainWindow` validation contour на named drag/drop pilot families..
│   │   │   │   │   └── test_random_order_validation_runtime.py  # Python-модуль: Проверить D-126 random-order / repeated-run validation contour на named drag/drop pilot..
│   │   │   │   ├── __init__.py  # Инициализация Python-пакета `drag_drop`.
│   │   │   │   ├── _drag_drop_test_helpers.py  # Python-модуль: Централизовать package-local re-export helpers для runtime drag/drop tests..
│   │   │   │   ├── _test_constants.py  # Python-модуль: Содержать единый источник case-id каталогов и числовых guard-порогов.
│   │   │   │   ├── test_foundation_runtime.py  # Python-модуль: Проверять базовые owner/runtime contracts workspace drag/drop..
│   │   │   │   ├── test_leakage_observability_runtime.py  # Python-модуль: Зафиксировать D-125 observability pilot contour для drag/drop..
│   │   │   │   ├── test_legacy_tail_runtime.py  # Python-модуль: Проверять residual tail runtime contracts legacy drag/drop harness..
│   │   │   │   ├── test_perimeter_runtime.py  # Python-модуль: Модуль проверяет perimeter runtime-сценарии drag/drop для edge-host и control path..
│   │   │   │   ├── test_session_recovery_runtime.py  # Python-модуль: Модуль проверяет session и recovery runtime-сценарии drag/drop после release и rollback..
│   │   │   │   └── test_shutdown_runtime.py  # Python-модуль: Проверять shutdown и lifecycle cleanup runtime contracts drag/drop..
│   │   │   ├── __init__.py  # Инициализация Python-пакета `workspace`.
│   │   │   ├── test_dock_panels_workspace_adapter_integration.py  # Python-модуль: Targeted integration tests for dock panels workspace adapter path..
│   │   │   ├── test_workspace_central_content_adapter_integration.py  # Python-модуль: Targeted integration tests for central content adapter wiring..
│   │   │   ├── test_workspace_runtime_integration.py  # Python-модуль: Focused integration tests проверяют связку `ZoneRegistry + WorkspaceEvents`.
│   │   │   ├── test_workspace_snapshot_round_trip.py  # Python-модуль: Integration-тесты для workspace snapshot persistence boundary..
│   │   │   └── test_workspace_toolbar_adapter_integration.py  # Python-модуль: Targeted integration tests for `C-100` toolbar bridge wiring..
│   │   └── __init__.py  # Инициализация Python-пакета `ui`.
│   ├── __init__.py  # Инициализация Python-пакета `integration`.
│   ├── conftest.py  # Python-модуль: Фикстуры для интеграционных тестов..
│   ├── test_main_integration.py  # Python-модуль: Комплексные тесты инициализации и жизненного цикла приложения AIFE..
│   ├── test_security_logging_e2e.py  # Python-модуль: E2E-интеграционный тест structured security logging потока (S-035/S-036/S-037)..
│   └── test_system_initializer_integration.py  # Python-модуль: Integration tests для SystemInitializer..
├── performance/  # Измерительные и производительные проверки.
│   ├── baselines/  # Каталог baselines; назначение уточняется по дочерним файлам.
│   │   ├── latest/  # Каталог latest; назначение уточняется по дочерним файлам.
│   │   │   └── .gitkeep  # Файл .gitkeep; роль определяется родительским каталогом.
│   │   ├── releases/  # Каталог releases; назначение уточняется по дочерним файлам.
│   │   │   └── .gitkeep  # Файл .gitkeep; роль определяется родительским каталогом.
│   │   ├── weekly/  # Каталог weekly; назначение уточняется по дочерним файлам.
│   │   │   └── .gitkeep  # Файл .gitkeep; роль определяется родительским каталогом.
│   │   ├── __init__.py  # Инициализация Python-пакета `baselines`.
│   │   ├── _baseline_tools.py  # Python-модуль: Shared helper layer для performance baseline lifecycle..
│   │   └── README.md  # Обзор и маршрут чтения: 📊 Baseline Management — Retention Policy.
│   ├── benchmarks/  # Каталог benchmarks; назначение уточняется по дочерним файлам.
│   │   ├── test_communication_performance.py  # Python-модуль: Performance benchmarks для текущего live communication contour..
│   │   └── test_core_performance.py  # Python-модуль: Performance benchmarks для текущего live core contour..
│   ├── harness/  # Каталог harness; назначение уточняется по дочерним файлам.
│   │   ├── ui/  # Интерфейс, рабочая область, панели, графики и визуальные компоненты.
│   │   │   ├── __init__.py  # Инициализация Python-пакета `ui`.
│   │   │   ├── README.md  # Обзор и маршрут чтения: UI Perf Harnesses (C-081 / C-102).
│   │   │   ├── test_chart_scalability_harness.py  # Python-модуль: Perf/scalability harness для ChartWidget (C-081)..
│   │   │   └── test_workspace_framework_closure_harness.py  # Python-модуль: Advisory perf evidence slot for workspace framework closure (`C-102`)..
│   │   ├── __init__.py  # Инициализация Python-пакета `harness`.
│   │   └── README.md  # Обзор и маршрут чтения: Performance Extensions (Domain-specific Harnesses).
│   ├── .pylintrc  # Файл .pylintrc; роль определяется родительским каталогом.
│   ├── __init__.py  # Инициализация Python-пакета `performance`.
│   ├── BENCHMARK_GUIDELINES.md  # Файл BENCHMARK GUIDELINES; роль определяется родительским каталогом.
│   ├── conftest.py  # Python-модуль: Performance testing fixtures и shared substrate..
│   └── README.md  # Обзор и маршрут чтения: 🚀 Performance Testing Infrastructure.
├── smoke/  # Быстрые проверки жизнеспособности.
│   ├── test_benchmark_smoke.py  # Python-модуль: Smoke benchmark test для STD-TEST-PERF-001..
│   ├── test_control_smoke.py  # Python-модуль: Контрольный модуль для быстрых smoke-прогонов в pre-commit..
│   └── test_strategy_tester_smoke.py  # Python-модуль: Smoke-тест полного UI flow для StrategyTesterPanel (C-049)..
├── unit/  # Unit-проверки и проверки валидаторов.
│   ├── server/  # Contract-driven pure-model proofs F3.
│   │   ├── test_access.py  # Result identity/provenance и explicit partial/error semantics.
│   │   ├── test_execution.py  # Lease/fence, stale rejection, renewal и reclaim authority generation.
│   │   ├── test_publication.py  # Publication order, four-proof ACK gate и resumable retry.
│   │   ├── test_runtime_composition.py  # Process roles и отсутствие global runtime singleton.
│   │   ├── test_scheduling.py  # Deterministic timezone-aware due identity и materialization separation.
│   │   ├── test_storage.py  # Narrow capability protocols и no-backend public boundary.
│   │   └── test_work.py  # Work lifecycle, illegal transitions и logical identity-preserving retry.
│   ├── analysis/  # Каталог analysis; назначение уточняется по дочерним файлам.
│   │   ├── test_check_backlog.py  # Python-модуль: Проверка локальных контрактов backlog-парсинга и AUTO-синхронизации..
│   │   ├── test_owner_corpus_normalization_d291.py  # Python-модуль: Проверка bounded execution-артефакта `D-291` и его синхронизации с control-plane..
│   │   ├── test_owner_corpus_normalization_d292.py  # Python-модуль: Проверка execution-артефакта `D-292`, прямого owner verdict и синхронизации с control-plane..
│   │   ├── test_owner_corpus_normalization_d293.py  # Python-модуль: Проверка bounded execution-артефакта `D-293`, follower-side sync и control-plane перехода к `D-294`..
│   │   ├── test_report_hook_health.py  # Python-модуль: Проверить advisory hook health report и repeat-failure routing policy..
│   │   ├── test_rollback_utils.py  # Python-модуль: Unit-тест для хелпера `assert_failing_initialization_behavior`..
│   │   ├── test_semantic_passthrough_audit.py  # Python-модуль: Проверить heuristic audit `semantic_passthrough_audit.py`..
│   │   ├── test_sort_incoming_icons.py  # Python-модуль: Тесты для scripts/sort_incoming_icons.py..
│   │   └── test_workaround_age_report.py  # Python-модуль: Проверить отчёт `workaround_age_report.py`..
│   ├── bootstrap/  # Каталог bootstrap; назначение уточняется по дочерним файлам.
│   │   ├── __init__.py  # Инициализация Python-пакета `bootstrap`.
│   │   ├── test_app_context_get_manager.py  # Python-модуль: Проверить поведение `AppContext.get_manager` после перехода.
│   │   ├── test_application_runner.py  # Python-модуль: Unit-тесты для `ApplicationRunner`..
│   │   ├── test_dependency_manager.py  # Python-модуль: Unit-тесты жизненного цикла DependencyManager..
│   │   └── test_main_logic.py  # Python-модуль: Unit-тесты fail-fast bootstrap-контракта `MainLogic.run()`..
│   ├── ci/  # Каталог ci; назначение уточняется по дочерним файлам.
│   │   ├── offline_hooks/  # Модульные доказательства автономных адаптеров хуков проверки коммита.
│   │   │   ├── __init__.py  # Граница тестового пакета автономных хуков.
│   │   │   └── test_detect_secrets.py  # Проверки CLI, порядка импортов и блокировки HTTP в адаптере detect-secrets.
│   │   ├── contracts/  # Контракты между поверхностями и процессами.
│   │   │   ├── __init__.py  # Инициализация Python-пакета `contracts`.
│   │   │   └── test_pre_push_fail_fast_contract.py  # Python-модуль: Защитить fail-fast contract для `pre-push` closure-proof contour..
│   │   ├── test_capture_test_operation_run.py  # Python-модуль: Проверить D-136 storage-contract wrapper для test-operation commands..
│   │   ├── test_run_coverage_thresholds.py  # Python-модуль: Проверки однострочного live-progress для coverage pre-push hook..
│   │   ├── test_run_fast_quality_gate.py  # Python-модуль: Проверить bounded planning и wrapper semantics для `run_fast_quality_gate.py`..
│   │   └── test_run_validated_xdist_contours.py  # Python-модуль: Тесты для contour-bounded optional xdist rollout helper..
│   ├── communication/  # Runtime-слой обмена событиями и сообщениями.
│   │   ├── event_bus/  # Каталог event bus; назначение уточняется по дочерним файлам.
│   │   │   ├── __init__.py  # Инициализация Python-пакета `event_bus`.
│   │   │   ├── _shared.py  # Python-модуль: Общие test doubles и fixtures для bounded `EventBus` unit-suite..
│   │   │   ├── test_event_bus_integration.py  # Python-модуль: Integration-like composition-root proofs для bounded `EventBus` unit-suite..
│   │   │   ├── test_event_bus_lifecycle.py  # Python-модуль: Lifecycle proofs для bounded `EventBus` unit-suite..
│   │   │   ├── test_event_bus_publish.py  # Python-модуль: Publish/scoped-topic proofs для bounded `EventBus` unit-suite..
│   │   │   └── test_event_bus_subscription.py  # Python-модуль: Subscribe/unsubscribe proofs для bounded `EventBus` unit-suite..
│   │   ├── log_manager/  # Каталог log manager; назначение уточняется по дочерним файлам.
│   │   │   ├── __init__.py  # Инициализация Python-пакета `log_manager`.
│   │   │   ├── test_log_manager.py  # Python-модуль: Набор unit-тестов для LogManager и глобального экземпляра `log_manager`..
│   │   │   └── test_log_manager_injection.py  # Python-модуль: Валидация DI (Dependency Injection) для `LogManager`..
│   │   ├── manager/  # Каталог manager; назначение уточняется по дочерним файлам.
│   │   │   └── test_communication_manager_shutdown.py  # Python-модуль: Focused regression-proof для shutdown cleanup в `CommunicationManager`..
│   │   ├── test_audit_logger.py  # Python-модуль: Unit-тесты для AuditLogger (S-037)..
│   │   ├── test_communication_package_surface.py  # Python-модуль: Проверить корневой package surface `communication`..
│   │   ├── test_elk_handler.py  # Python-модуль: Unit-тесты для ElasticsearchHandler (S-040)..
│   │   ├── test_error_handling.py  # Python-модуль: Проверить, что локальный cleanup `D-098` не ломает живой decorator path.
│   │   ├── test_event_router.py  # Python-модуль: Unit-тесты для EventRouter..
│   │   ├── test_log_retention.py  # Python-модуль: Unit-тесты retention policy и архивирования логов (S-042)..
│   │   ├── test_pii_masker.py  # Python-модуль: Unit-тесты для PII masking utilities (S-039)..
│   │   └── test_security_logger.py  # Python-модуль: Unit-тесты для SecurityLogger (S-035)..
│   ├── core/  # Базовые сервисы, управление, данные, API и доменная логика.
│   │   ├── data/  # Каталог data; назначение уточняется по дочерним файлам.
│   │   │   ├── test_data_package_surface.py  # Python-модуль: Проверить package-first contract для `core.data` после `D-076`..
│   │   │   └── test_data_repository_taxonomy.py  # Python-модуль: Материализовать repository-unit proof slice для `D-079`..
│   │   └── management/  # Каталог management; назначение уточняется по дочерним файлам.
│   │       └── test_system_control_manager.py  # Python-модуль: Unit-тесты для SystemControlManager..
│   ├── diagrams/  # Каталог diagrams; назначение уточняется по дочерним файлам.
│   │   └── test_export_diagrams.py  # Python-модуль: Focused proof contour для `scripts.diagrams.export_diagrams`..
│   ├── main_entrypoint/  # Каталог main entrypoint; назначение уточняется по дочерним файлам.
│   │   ├── __init__.py  # Инициализация Python-пакета `main_entrypoint`.
│   │   ├── _shared.py  # Python-модуль: Bounded shared helpers для semantic slices suite `main.py`..
│   │   ├── test_amain_runtime.py  # Python-модуль: Semantic slice для async composition-root proof family в `main.py`..
│   │   ├── test_cleanup_and_regressions.py  # Python-модуль: Semantic slice для cleanup/regression proof family в `main.py`..
│   │   ├── test_env_and_logging.py  # Python-модуль: Semantic slice для env/logging proof family в `main.py`..
│   │   ├── test_graceful_shutdown.py  # Python-модуль: Semantic slice для graceful shutdown proof family в `main.py`..
│   │   └── test_main_exit_paths.py  # Python-модуль: Semantic slice для sync exit-path proof family в `main.py`..
│   ├── monitoring/  # Runtime-поддержка мониторинга и наблюдаемости.
│   │   ├── test_monitoring_manager.py  # Python-модуль: Focused async regression-тесты для `MonitoringManager` в рамках `D-077`..
│   │   ├── test_monitoring_package_surface.py  # Python-модуль: Проверить package surface корневого пакета `monitoring`..
│   │   ├── test_performance_baseline_tools.py  # Python-модуль: Regression tests для materialized performance baseline tooling..
│   │   └── test_security_alerts.py  # Python-модуль: Unit-тесты для security alert rules (S-041)..
│   ├── patterns/  # Unit-доказательства текущего договора пакета patterns.
│   │   └── test_patterns_contract.py  # Python-модуль: Проверить публичную поверхность, lifecycle-сигналы и обработку ошибок текущего `patterns`.
│   ├── scripts/  # Инструменты проверки, сборки, обслуживания и измерения.
│   │   ├── quality_toolchain/  # Unit-доказательства profile, carrier и fail-closed execution contour.
│   │   │   ├── __init__.py  # Минимальная граница test package без scenarios и fixtures.
│   │   │   ├── _fixtures.py  # Общие typed fixtures quality-toolchain tests без production logic.
│   │   │   ├── dependencies/  # Dependency closure и missing-capability semantic-routing regressions.
│   │   │   │   ├── __init__.py  # Semantic test-package boundary без production logic.
│   │   │   │   ├── _capability_fixtures.py  # Test-only trusted-context builders без production authority.
│   │   │   │   ├── test_capability_applicability.py  # Capability kind/domain/task/profile applicability и bureaucracy controls.
│   │   │   │   └── test_capability_route.py  # Provenance, UNKNOWN relation и reusable-policy/task-context regressions.
│   │   │   ├── test_orchestration.py  # Windows/WSL2 host adapter и одношаговый dispatch.
│   │   │   ├── artifact/  # Доказательства builder, identity и carrier verification.
│   │   │   │   ├── __init__.py  # Минимальная граница artifact test package.
│   │   │   │   ├── builder/  # Builder и component-carrier scenarios по отдельным semantic owners.
│   │   │   │   │   ├── __init__.py  # Граница builder test package.
│   │   │   │   │   ├── _support.py  # Offline carrier fixtures и exact component bindings.
│   │   │   │   │   ├── test_carrier.py  # Repository-owned carrier CLI и deterministic SHA.
│   │   │   │   │   └── test_core.py  # Builder policy, materialization и provenance scenarios.
│   │   │   │   ├── runtime/  # Standalone runtime-authority producer и verifier regressions.
│   │   │   │   │   └── test_authority_producer.py  # Predecessor-free current producer, deterministic A/B и fail-closed source bindings.
│   │   │   │   ├── test_identity.py  # Repository recipe bytes и schema/builder identity parity.
│   │   │   │   ├── test_semantic_carrier_reuse.py  # HEAD-independent reuse при неизменном producer closure.
│   │   │   │   └── test_verification.py  # Entry digests, duplicate paths, ELF и stale receipt rejection.
│   │   │   ├── refresh/  # Reusable regression-доказательства refresh/result terminal lifecycle.
│   │   │   │   └── test_network_lifecycle.py  # RESULT-before-PASS, crash/interruption, payload и attempt-identity regressions.
│   │   │   ├── operator/  # Проверки операторского выбора quality-команд и agent-facing маршрута.
│   │   │   │   ├── __init__.py  # Граница тестового пакета операторского слоя.
│   │   │   │   └── test_agent_check.py  # Автоматический выбор проверок и fail-closed сценарии команды `check`.
│   │   │   └── execution/  # Доказательства offline bootstrap и network/process enforcement.
│   │   │       ├── capability/  # Physical provenance и executable semantic-consumer regressions.
│   │   │       │   └── test_consumer.py  # Live consumer, fail-closed RC и task-context parser regressions.
│   │   │       ├── __init__.py  # Минимальная граница execution test package.
│   │   │       ├── bootstrap/  # Bootstrap core и host-bound platform boundaries.
│   │   │       ├── platforms/  # Syscall observer и event-time executable identity.
│   │   │       ├── pre_freeze/  # Identity parity и physical archive-only route.
│   │   │       ├── runtime_inventory/  # Runtime closure и hook preparation inventory.
│   │   │       ├── test_negative_corpus.py  # Adversarial stale, mutation и post-bootstrap network corpus.
│   │   │       └── test_runner.py  # Terminal receipt и fail-closed execution lifecycle.
│   │   ├── _review_package_test_support.py  # Общие bounded Git/archive/carrier builders review-package tests.
│   │   ├── test_build_review_package.py  # Core review-package build, check, publish и latest semantics.
│   │   ├── test_build_review_package_carrier.py  # Object carrier, pack reconstruction и publication identity scenarios.
│   │   ├── test_materialize_review_package.py  # Materializer CLI, run-scoped bytes и finalization binding.
│   │   ├── authorized_execution_bundle/  # Unit-доказательства ZIP, schema и порядка owner transition.
│   │   │   ├── __init__.py  # Инициализация смыслового тестового пакета bundle.
│   │   │   ├── recovery/  # Реальный lifecycle recovery, replay и owner transition fixtures.
│   │   │   ├── test_archive.py  # Archive-only build, schema drift и ZIP safety.
│   │   │   ├── test_recovery.py  # Fail-closed recovery marker, replay facts и классификация отказов.
│   │   │   └── test_runtime.py  # Preflight, replay и clean-clone preflight/execute acceptance.
│   │   ├── direct_patch/  # Unit/security/smoke доказательства canonical direct executor.
│   │   │   ├── __init__.py  # Инициализация тестового пакета direct patch.
│   │   │   ├── _support.py  # Изолированные Git/package helpers и selective stubs тяжёлых gates.
│   │   │   ├── test_executor_smoke.py  # Success, failure, rollback, retry, lock, rename/mode и commit-hook matrix.
│   │   │   ├── test_owner_authorization_transition.py  # Authority scope, lifecycle и end-to-end owner authorizer bridge.
│   │   │   ├── test_package.py  # Strict ZIP/YAML/schema и transport security tests.
│   │   │   ├── test_policy_and_proof.py  # Protected scope и expected_head-bound proof policy.
│   │   │   ├── owner_transition/  # Доказательства rolling authorization и lifecycle-перехода профилей.
│   │   │   │   └── test_rolling.py  # Receipt/review binding и точный переход allowed_once в consumed.
│   │   │   ├── rollback/  # Регрессии точного rollback и восстановления чистого Git-состояния.
│   │   │   │   └── test_filter_stat_cleanliness.py  # Windows text/filter-stat residue, bounded reindex и fail-closed drift.
│   │   │   └── routes/  # Unit и Git-derived доказательства bootstrap/finalize профилей.
│   │   │       ├── __init__.py  # Граница тестового пакета lifecycle-маршрутов.
│   │   │       ├── _fixtures.py  # Компактные типизированные модели route manifest.
│   │   │       ├── test_bootstrap.py  # Prepared audit/TZ/blocked PRR и запрет самоавторизации.
│   │   │       ├── test_confirmation.py  # Schema и внешний owner confirmation gate.
│   │   │       └── test_finalization.py  # Terminal-only transition, lineage и retention review ZIP.
│   │   ├── patch_runtime/  # Доказательства общего repository lock и fail-closed process identity.
│   │   │   ├── __init__.py  # Граница unit-пакета mutation runtime.
│   │   │   ├── test_mutation_lock.py  # Конкуренция маршрутов, linked worktree и точное stale recovery.
│   │   │   └── test_process_identity.py  # Windows/Linux process identity и недоступные процессы.
│   │   ├── patch_workspace/  # Unit-доказательства общего path budget и lifecycle временной аренды.
│   │   │   ├── __init__.py  # Граница unit-пакета общего path runtime.
│   │   │   └── test_path_runtime.py  # Drive root, segment budget, Git argv и fail-closed cleanup.
│   │   ├── verified_patch_handoff/  # Unit-доказательства builder, executor, reporting, repair recovery и producer boundary.
│   │   │   ├── test_candidate_preparation.py  # Бюджет временной области и готовность репетиции D-378.
│   │   │   ├── test_scope_budget.py  # Канонический бюджет области и привязка Task Proof.
│   │   │   ├── lineage/  # Доказательства классификации промежуточных commit относительно кандидата.
│   │   │   │   ├── __init__.py  # Граница тестового пакета lineage.
│   │   │   │   └── test_classification.py  # Disjoint, candidate-equivalent и conflicting сценарии.
│   │   │   ├── receipt/  # Доказательства неизменяемого execution receipt и review binding.
│   │   │   │   ├── __init__.py  # Граница тестового пакета receipt.
│   │   │   │   └── test_store.py  # Идемпотентность, конфликт результата и порядок сохранения review.
│   │   │   ├── worktree/  # Доказательства изолированного commit и атомарной projection.
│   │   │   │   ├── __init__.py  # Граница тестового пакета worktree.
│   │   │   │   └── test_session.py  # Retained failure workspace и fast-forward успешного commit.
│   │   │   ├── patch_binding/  # Изолированные regression-доказательства exact source/frozen binding и transactional freeze.
│   │   │   │   └── test_builder_patch_binding.py  # Bound-фаза, exact SHA-256 и атомарная фиксация нормализованного patch.
│   │   │   ├── normalization/  # Изолированные доказательства policy 2.0/3.0 и порядка isort -> Black до фиксации кандидата.
│   │   │   │   └── test_candidate_normalization_policy.py  # Точное связывание версий, конфигурации и порядка formatter.
│   │   │   ├── reanchor/  # Git-derived доказательства предавторизационной перепривязки кандидата.
│   │   │   │   ├── __init__.py  # Инициализация тестового подпакета перепривязки.
│   │   │   │   └── test_candidate_reanchor.py  # Успешная цепочка, identity drift и lineage-отказы.
│   │   │   ├── __init__.py  # Инициализация тестового пакета verified patch handoff.
│   │   │   ├── _executor_test_support.py  # Общие Git/carrier helpers без самостоятельной test collection.
│   │   │   ├── test_authorization.py  # Task Contract profiles, exact authorization commit и schema 3 binding.
│   │   │   ├── test_builder.py  # Builder, manifest и instruction compatibility.
│   │   │   ├── test_candidate_validation.py  # Detached producer worktree и zero-diff candidate gate.
│   │   │   ├── test_executor.py  # State machine, execute/resume, commit и publish boundary.
│   │   │   ├── test_repair.py  # Repair-resume/amend, proof context и attempt lifecycle.
│   │   │   ├── test_reporting.py  # Compact/live output, bounded tails и runtime reports.
│   │   │   └── test_staging.py  # Идемпотентные add/modify/delete/rename и exact staged set.
│   │   ├── benchmarks/  # Каталог benchmarks; назначение уточняется по дочерним файлам.
│   │   │   ├── owner_artifact_derived_json_generation_and_continuity/  # Каталог owner artifact derived json generation and continuity; назначение уточняется по дочерним файлам.
│   │   │   │   ├── __init__.py  # Инициализация Python-пакета `owner_artifact_derived_json_generation_and_continuity`.
│   │   │   │   ├── test_d301.py  # Python-модуль: Unit proof for D-301 measurement wrapper registration..
│   │   │   │   ├── test_d302.py  # Python-модуль: Unit proof for D-302 publication trace and wrapper closure..
│   │   │   │   ├── test_i1032.py  # Python-модуль: Unit proof for I-1032 semantic T0 baseline..
│   │   │   │   ├── test_i1033.py  # Python-модуль: Unit proof for I-1033 navigation T0-MD baseline..
│   │   │   │   └── test_i1034.py  # Python-модуль: Unit proof for I-1034 post-D300 result and first compare package..
│   │   │   ├── owner_artifact_existing_corpus_normalization/  # Каталог owner artifact existing corpus normalization; назначение уточняется по дочерним файлам.
│   │   │   │   ├── __init__.py  # Инициализация Python-пакета `owner_artifact_existing_corpus_normalization`.
│   │   │   │   ├── test_d295.py  # Python-модуль: Unit proof for D-295 measurement wrapper registration..
│   │   │   │   ├── test_d296.py  # Python-модуль: Unit proof for D-296 publication trace and wrapper closure..
│   │   │   │   ├── test_i1027.py  # Python-модуль: Unit proof for I-1027 semantic T0 baseline..
│   │   │   │   ├── test_i1028.py  # Python-модуль: Unit proof for I-1028 navigation T0 baseline..
│   │   │   │   └── test_i1029.py  # Python-модуль: Unit proof for I-1029 post-D294 result and first compare package..
│   │   │   ├── owner_artifact_publication/  # Каталог owner artifact publication; назначение уточняется по дочерним файлам.
│   │   │   │   └── test_i1024.py  # Python-модуль: Unit proof for I-1024 owner-artifact-publication T1 result and compare..
│   │   │   ├── owner_corpus_semantic_block_normalization_rollout_t0_wrapper/  # Каталог owner corpus semantic block normalization rollout t0 wrapper; назначение уточняется по дочерним файлам.
│   │   │   │   ├── __init__.py  # Инициализация Python-пакета `owner_corpus_semantic_block_normalization_rollout_t0_wrapper`.
│   │   │   │   ├── test_d311.py  # Python-модуль: Unit proof for D-311/D-312/I-1041/I-1042 measurement wrapper substrate..
│   │   │   │   ├── test_d313_manifest.py  # Python-модуль: Unit proof for D-313 family-local immutability/admissibility manifest..
│   │   │   │   └── test_i1044.py  # Python-модуль: Unit proof for I-1044 changed-slice compare package..
│   │   │   ├── owner_semantic_catalog_layer_measurement/  # Каталог owner semantic catalog layer measurement; назначение уточняется по дочерним файлам.
│   │   │   │   ├── __init__.py  # Инициализация Python-пакета `owner_semantic_catalog_layer_measurement`.
│   │   │   │   ├── test_d307.py  # Python-модуль: Unit proof for D-307 registration invariants after D-308..
│   │   │   │   ├── test_d308.py  # Python-модуль: Unit proof for D-308 full scenario catalog contract..
│   │   │   │   ├── test_d309.py  # Python-модуль: Unit proof for D-309 companion-only publication trace..
│   │   │   │   ├── test_i1037.py  # Python-модуль: Unit proof for I-1037 semantic T0 baseline..
│   │   │   │   ├── test_i1038.py  # Python-модуль: Unit proof for I-1038 navigation T0-MD baseline..
│   │   │   │   ├── test_i1039.py  # Python-модуль: Unit proof for I-1039 post-D306 normalized result..
│   │   │   │   └── test_i1040.py  # Python-модуль: Unit proof for I-1040 first compare package..
│   │   │   ├── verified_patch_handoff_v3/  # Регистрационные доказательства измерительного семейства verified patch handoff v3.
│   │   │   │   └── test_registration.py  # Проверка schema-valid registration-only family без фиктивных baseline/result/dashboard artifacts.
│   │   │   ├── publication/  # Каталог publication; назначение уточняется по дочерним файлам.
│   │   │   │   └── test_semantic_navigation_publication_i1022.py  # Python-модуль: Целевое доказательство I-1022: publication package и trace provenance.
│   │   │   ├── __init__.py  # Инициализация Python-пакета `benchmarks`.
│   │   │   ├── test_benchmark_adapter_bridge.py  # Python-модуль: Unit proof: bounded adapter bridge для I-1011..
│   │   │   ├── test_benchmark_storage_boundary.py  # Python-модуль: Unit proof: граница хранилища нормализованных доказательств для I-1012..
│   │   │   ├── test_semantic_navigation_compare_i1021.py  # Python-модуль: Целевое доказательство I-1021: compare-package и пороговый вывод Topic 20..
│   │   │   ├── test_semantic_navigation_corpus_i1014.py  # Python-модуль: Тесты для I-1014 corpus descriptor и scenario catalog..
│   │   │   ├── test_semantic_navigation_regression_package_i1020.py  # Python-модуль: Unit proof: первый normalized regression package для `I-1020`..
│   │   │   ├── test_semantic_navigation_scenarios_i1015.py  # Python-модуль: Тесты для I-1015: AGENTS-first сценарии и contamination matrix..
│   │   │   ├── test_semantic_navigation_scenarios_i1016.py  # Python-модуль: Тесты для I-1016: standards registry-first и route-back contamination guard..
│   │   │   ├── test_semantic_navigation_scenarios_i1017.py  # Python-модуль: Тесты для I-1017: ADR registry-first маршрут и bounded history redirect recovery..
│   │   │   ├── test_semantic_navigation_scenarios_i1018.py  # Python-модуль: Тесты для I-1018: классификация contract и маршрут Artifact Contract..
│   │   │   ├── test_semantic_navigation_scenarios_i1019.py  # Python-модуль: Тесты для I-1019: маршруты слоёв prompt, consumer и companion..
│   │   │   └── test_sync_gates_i1013.py  # Python-модуль: Unit-тесты для проверочных шлюзов синхронизации (I-1013)..
│   │   ├── __init__.py  # Инициализация Python-пакета `scripts`.
│   │   └── test_validate_structure.py  # Python-модуль: Проверка bounded execution-section enforcement в `validate_structure.py`..
│   ├── security/  # Слой безопасности, валидации, сканирования и защитных правил.
│   │   ├── communication/  # Runtime-слой обмена событиями и сообщениями.
│   │   │   ├── __init__.py  # Инициализация Python-пакета `communication`.
│   │   │   ├── test_adapter_no_leak.py  # Python-модуль: Проверить, что SecurityCommunicationAdapter логирует только sanitized payload..
│   │   │   ├── test_dispatcher_no_raw_payload.py  # Python-модуль: Проверить, что SecurityEventDispatcher не логирует raw payload в dispatch()..
│   │   │   ├── test_dispatcher_warning_levels.py  # Python-модуль: Проверить escalation уровней логирования и masking session_id в SecurityEventDispatcher..
│   │   │   └── test_payload_sanitizer.py  # Python-модуль: Unit tests для security.utils.payload_sanitizer..
│   │   ├── controls/  # Каталог controls; назначение уточняется по дочерним файлам.
│   │   │   ├── policy_review/  # Каталог policy review; назначение уточняется по дочерним файлам.
│   │   │   │   ├── __init__.py  # Инициализация Python-пакета `policy_review`.
│   │   │   │   ├── test_error_review_policy.py  # Python-модуль: Тесты runtime-реализации disclosure/review policy контролей..
│   │   │   │   ├── test_review_owasp_checks.py  # Python-модуль: Тесты runtime-реализации OWASP/review контролей..
│   │   │   │   └── test_secrets_policy.py  # Python-модуль: Тесты runtime-реализации secrets management контролей..
│   │   │   ├── __init__.py  # Инициализация Python-пакета `controls`.
│   │   │   ├── test_api_security_crypto.py  # Python-модуль: Тесты runtime-реализации API security и crypto контролей..
│   │   │   ├── test_auth_session_jwt.py  # Python-модуль: Тесты runtime-реализации auth/session/JWT контролей..
│   │   │   ├── test_blockchain_security.py  # Python-модуль: Тесты runtime-реализации blockchain security контролей..
│   │   │   ├── test_content_file_guard.py  # Python-модуль: Тесты runtime-реализации content/file guard контролей..
│   │   │   ├── test_in_memory_eviction.py  # Python-модуль: Тесты eviction/cleanup для in-memory storages security-подсистемы..
│   │   │   ├── test_key_mgmt_tls_query.py  # Python-модуль: Тесты runtime-реализации key management, TLS и query guard контролей..
│   │   │   └── test_mfa_authz.py  # Python-модуль: Тесты runtime-реализации MFA и authorization контролей..
│   │   ├── integration/  # Интеграционные проверки связей между слоями.
│   │   │   ├── auth_access/  # Каталог auth access; назначение уточняется по дочерним файлам.
│   │   │   │   ├── __init__.py  # Инициализация Python-пакета `auth_access`.
│   │   │   │   ├── test_security_manager_auth_integration.py  # Python-модуль: Интеграционные unit-тесты runtime auth-контролей в SecurityManager..
│   │   │   │   └── test_security_manager_mfa_authz_integration.py  # Python-модуль: Интеграционные unit-тесты MFA/authz-контролей в SecurityManager..
│   │   │   ├── __init__.py  # Инициализация Python-пакета `integration`.
│   │   │   ├── test_security_manager_api_security_crypto_integration.py  # Python-модуль: Интеграционные unit-тесты API/crypto-контролей в SecurityManager..
│   │   │   ├── test_security_manager_blockchain_security_integration.py  # Python-модуль: Интеграционные unit-тесты blockchain security-контролей в SecurityManager..
│   │   │   ├── test_security_manager_content_file_guard_integration.py  # Python-модуль: Интеграционные unit-тесты content/file-guard контролей в SecurityManager..
│   │   │   ├── test_security_manager_error_review_policy_integration.py  # Python-модуль: Интеграционные unit-тесты error/review policy-контролей в SecurityManager..
│   │   │   ├── test_security_manager_key_mgmt_tls_query_integration.py  # Python-модуль: Интеграционные unit-тесты key-mgmt/TLS/query-контролей в SecurityManager..
│   │   │   ├── test_security_manager_review_owasp_checks_integration.py  # Python-модуль: Интеграционные unit-тесты OWASP/review контролей в SecurityManager..
│   │   │   └── test_security_manager_secrets_policy_integration.py  # Python-модуль: Интеграционные unit-тесты secrets policy-контролей в SecurityManager..
│   │   ├── __init__.py  # Инициализация Python-пакета `security`.
│   │   ├── conftest.py  # Python-модуль: Общие fixtures для integration-тестов security-модуля..
│   │   └── test_security_package_surface.py  # Python-модуль: Проверить минимальный package surface корневого пакета `security`..
│   ├── standards/  # Стандарты проекта.
│   │   ├── __init__.py  # Инициализация Python-пакета `standards`.
│   │   ├── test_registry_generator_json.py  # Python-модуль: Проверка корректности JSON companion-экспорта в registry_generator:.
│   │   └── test_semantic_catalog_generation.py  # Python-модуль: Проверить helper-слой semantic catalog generation для owner-side карты.
│   ├── system_initializer/  # Каталог system initializer; назначение уточняется по дочерним файлам.
│   │   ├── __init__.py  # Инициализация Python-пакета `system_initializer`.
│   │   ├── _shared.py  # Python-модуль: Общие bounded fixtures и helpers для semantic slices `SystemInitializer`..
│   │   ├── test_component_shutdown.py  # Python-модуль: Semantic slice для component-shutdown proof family `SystemInitializer`..
│   │   ├── test_event_bus_and_stop_event.py  # Python-модуль: Semantic slice для EventBus/app_stop proof family `SystemInitializer`..
│   │   ├── test_initialize_system.py  # Python-модуль: Semantic slice для initialization proof family `SystemInitializer`..
│   │   ├── test_pending_tasks.py  # Python-модуль: Semantic slice для pending-tasks drain proof family `SystemInitializer`..
│   │   ├── test_properties_and_loop_checks.py  # Python-модуль: Semantic slice для state/property/loop proof family `SystemInitializer`..
│   │   └── test_shutdown_paths.py  # Python-модуль: Semantic slice для shutdown orchestration proof family `SystemInitializer`..
│   ├── ui/  # Интерфейс, рабочая область, панели, графики и визуальные компоненты.
│   │   ├── action_registry/  # Каталог action registry; назначение уточняется по дочерним файлам.
│   │   │   ├── __init__.py  # Инициализация Python-пакета `action_registry`.
│   │   │   ├── test_action_registry_descriptors.py  # Python-модуль: Проверить descriptor API реестра действий UI..
│   │   │   ├── test_action_registry_init_signals.py  # Python-модуль: Проверить инициализацию ActionRegistry и его legacy Qt-сигналы..
│   │   │   └── test_action_registry_unavailable_routing.py  # Python-модуль: Проверить canonical unavailable-routing для `ActionRegistry`..
│   │   ├── base_components/  # Каталог base components; назначение уточняется по дочерним файлам.
│   │   │   ├── settings/  # Каталог settings; назначение уточняется по дочерним файлам.
│   │   │   │   ├── __init__.py  # Инициализация Python-пакета `settings`.
│   │   │   │   ├── test_settings_loader.py  # Python-модуль: Unit-тесты для SettingsLoader..
│   │   │   │   └── test_ui_settings.py  # Python-модуль: Unit-тесты для UISettings..
│   │   │   ├── test_base_dialog.py  # Python-модуль: Unit-тесты для BaseAIFEDialog (синхронизация темы/типографики)..
│   │   │   ├── test_base_widget.py  # Python-модуль: Unit-тесты для BaseWidget..
│   │   │   ├── test_event_dispatcher.py  # Python-модуль: Unit-тесты для EventDispatcher и GlobalEventController..
│   │   │   ├── test_localization.py  # Python-модуль: Unit-тесты сервиса локализации UI..
│   │   │   ├── test_notifications.py  # Python-модуль: Unit-тесты Notification Center (C-054)..
│   │   │   ├── test_render_budget_manager.py  # Python-модуль: Unit-тесты для C-080: RenderBudgetManager + DataThrottlePolicy..
│   │   │   ├── test_transparent_icon_button.py  # Python-модуль: Unit-тесты для TransparentIconButton..
│   │   │   └── test_user_telemetry.py  # Python-модуль: Unit-тесты C-056 для User Telemetry (interaction + action logger)..
│   │   ├── communication/  # Runtime-слой обмена событиями и сообщениями.
│   │   │   ├── integration/  # Интеграционные проверки связей между слоями.
│   │   │   │   ├── __init__.py  # Инициализация Python-пакета `integration`.
│   │   │   │   ├── test_dock_manager_comm_integration.py  # Python-модуль: Проверить wiring-интеграцию DockPanelsManager со слоем UI communication..
│   │   │   │   └── test_main_window_comm_integration.py  # Python-модуль: Модуль проверяет integration-связку `MainWindow` с UI communication layer..
│   │   │   ├── runtime_layer/  # Каталог runtime layer; назначение уточняется по дочерним файлам.
│   │   │   │   ├── __init__.py  # Инициализация Python-пакета `runtime_layer`.
│   │   │   │   ├── test_connection_tracker.py  # Python-модуль: Проверить lifecycle и статусные контракты `ConnectionTracker`..
│   │   │   │   ├── test_ui_event_listener.py  # Python-модуль: Модуль проверяет unit-сценарии для `UIEventListener`..
│   │   │   │   ├── test_ui_log_consumer.py  # Python-модуль: Проверить lifecycle и буферные контракты `UILogConsumer`..
│   │   │   │   └── test_ui_state_updater.py  # Python-модуль: Модуль проверяет unit-сценарии для `UIStateUpdater`..
│   │   │   ├── __init__.py  # Инициализация Python-пакета `communication`.
│   │   │   ├── _ui_comm_test_helpers.py  # Python-модуль: Предоставить общие helper-функции для тестов UI communication..
│   │   │   └── test_ui_comm_adapter.py  # Python-модуль: Unit-тесты для UICommunicationAdapter..
│   │   ├── layout/  # Каталог layout; назначение уточняется по дочерним файлам.
│   │   │   ├── chart/  # Каталог chart; назначение уточняется по дочерним файлам.
│   │   │   │   ├── components/  # Каталог components; назначение уточняется по дочерним файлам.
│   │   │   │   │   ├── chart_tab_manager/  # Каталог chart tab manager; назначение уточняется по дочерним файлам.
│   │   │   │   │   │   ├── __init__.py  # Инициализация Python-пакета `chart_tab_manager`.
│   │   │   │   │   │   ├── test_chart_tab_manager_bottom_zone.py  # Python-модуль: Модуль проверяет unit-сценарии `BottomTabZone` в составе `ChartTabManager`..
│   │   │   │   │   │   ├── test_chart_tab_manager_tab_ops.py  # Python-модуль: Проверить tab-операции `ChartTabManager` в отдельном semantic slice..
│   │   │   │   │   │   ├── test_chart_tab_manager_theme.py  # Python-модуль: Модуль проверяет theme, style и related state-сценарии `ChartTabManager`..
│   │   │   │   │   │   └── test_chart_tab_manager_workspace_state.py  # Python-модуль: Модуль проверяет workspace persistence-сценарии `ChartTabManager`..
│   │   │   │   │   ├── __init__.py  # Инициализация Python-пакета `components`.
│   │   │   │   │   ├── test_chart_context_menu.py  # Python-модуль: Проверить context-menu contract для `ChartWidget`..
│   │   │   │   │   ├── test_chart_header_footer.py  # Python-модуль: Проверить header/footer contract для chart-компонентов..
│   │   │   │   │   └── test_chart_header_panel.py  # Python-модуль: Модуль проверяет unit-сценарии для `ChartHeaderPanel`..
│   │   │   │   ├── core/  # Базовые сервисы, управление, данные, API и доменная логика.
│   │   │   │   │   ├── __init__.py  # Инициализация Python-пакета `core`.
│   │   │   │   │   ├── test_chart_layer_incremental.py  # Python-модуль: Проверить incremental rendering contract для `ChartLayer` и `CandlestickItem`..
│   │   │   │   │   ├── test_chart_main_canvas_contract.py  # Python-модуль: Проверить основной canvas contract для `ChartWidget`..
│   │   │   │   │   ├── test_chart_runtime_contract.py  # Python-модуль: Модуль проверяет unit-сценарии для runtime-контракта chart workspace..
│   │   │   │   │   ├── test_chart_widget.py  # Python-модуль: Модуль проверяет базовые unit-сценарии для `ChartWidget`..
│   │   │   │   │   └── test_chart_workspace_state.py  # Python-модуль: Проверить serialization contract для `ChartWorkspaceState`..
│   │   │   │   ├── integrations/  # Каталог integrations; назначение уточняется по дочерним файлам.
│   │   │   │   │   ├── indicator_windows/  # Каталог indicator windows; назначение уточняется по дочерним файлам.
│   │   │   │   │   │   ├── layout/  # Каталог layout; назначение уточняется по дочерним файлам.
│   │   │   │   │   │   │   ├── __init__.py  # Инициализация Python-пакета `layout`.
│   │   │   │   │   │   │   ├── test_indicator_splitter_layout.py  # Python-модуль: Модуль проверяет layout и splitter-сценарии indicator windows..
│   │   │   │   │   │   │   └── test_indicator_time_axis_strip.py  # Python-модуль: Проверить dedicated time-axis strip contract для indicator windows..
│   │   │   │   │   │   ├── __init__.py  # Инициализация Python-пакета `indicator_windows`.
│   │   │   │   │   │   ├── test_indicator_window_chart_integration.py  # Python-модуль: Модуль проверяет integration-сценарии indicator windows с `ChartTabManager` и `ChartWidget`..
│   │   │   │   │   │   └── test_indicator_window_factory.py  # Python-модуль: Проверить factory и базовые window-level contracts indicator windows..
│   │   │   │   │   ├── __init__.py  # Инициализация Python-пакета `integrations`.
│   │   │   │   │   ├── test_data_stream_manager.py  # Python-модуль: Проверить integration contract для `DataStreamManager`..
│   │   │   │   │   ├── test_historical_data_loader.py  # Python-модуль: Модуль проверяет unit-сценарии для `HistoricalDataLoader`..
│   │   │   │   │   └── test_multi_chart_manager.py  # Python-модуль: Проверить coordination contract для `MultiChartManager`..
│   │   │   │   ├── utilities/  # Каталог utilities; назначение уточняется по дочерним файлам.
│   │   │   │   │   ├── __init__.py  # Инициализация Python-пакета `utilities`.
│   │   │   │   │   ├── test_chart_tools.py  # Python-модуль: Модуль проверяет unit-сценарии для `chart_tools` и drawing tools manager..
│   │   │   │   │   ├── test_chart_utilities.py  # Python-модуль: Проверить utility contracts для shortcut и layout managers..
│   │   │   │   │   └── test_chart_visibility_axes.py  # Python-модуль: Проверить visibility presets и axis contracts для `ChartWidget`..
│   │   │   │   ├── __init__.py  # Инициализация Python-пакета `chart`.
│   │   │   │   └── _chart_test_helpers.py  # Python-модуль: Собрать общие helper-функции для unit-тестов семейства `ui.layout.chart`..
│   │   │   ├── dialogs/  # Каталог dialogs; назначение уточняется по дочерним файлам.
│   │   │   │   ├── __init__.py  # Инициализация Python-пакета `dialogs`.
│   │   │   │   ├── test_in_app_help_dialog.py  # Python-модуль: Проверить bounded dialog встроенной справки..
│   │   │   │   └── test_in_app_help_loader.py  # Python-модуль: Проверить bounded loader встроенной справки AIFE..
│   │   │   ├── dock_panels/  # Каталог dock panels; назначение уточняется по дочерним файлам.
│   │   │   │   ├── manager/  # Каталог manager; назначение уточняется по дочерним файлам.
│   │   │   │   │   ├── drop_intents/  # Каталог drop intents; назначение уточняется по дочерним файлам.
│   │   │   │   │   │   ├── main_surface/  # Каталог main surface; назначение уточняется по дочерним файлам.
│   │   │   │   │   │   │   ├── __init__.py  # Инициализация Python-пакета `main_surface`.
│   │   │   │   │   │   │   ├── test_main_surface_host_mode.py  # Python-модуль: Unit-тесты host-mode сценариев для main-surface drop intents..
│   │   │   │   │   │   │   └── test_main_surface_repeated_inserts.py  # Python-модуль: Unit-тесты repeated insert сценариев для main-surface drop intents..
│   │   │   │   │   │   ├── perimeter/  # Каталог perimeter; назначение уточняется по дочерним файлам.
│   │   │   │   │   │   │   ├── __init__.py  # Инициализация Python-пакета `perimeter`.
│   │   │   │   │   │   │   ├── test_perimeter_restore_geometry.py  # Python-модуль: Unit-тесты perimeter restore и geometry сценариев для drop intents..
│   │   │   │   │   │   │   ├── test_perimeter_routing.py  # Python-модуль: Unit-тесты perimeter routing сценариев для drop intents..
│   │   │   │   │   │   │   └── test_perimeter_runtime_guards.py  # Python-модуль: Unit-тесты late-runtime guard сценариев для perimeter drop intents..
│   │   │   │   │   │   ├── __init__.py  # Инициализация Python-пакета `drop_intents`.
│   │   │   │   │   │   └── test_drop_intents_owner_apply.py  # Python-модуль: Unit-тесты owner apply сценариев для drop intents `DockPanelsManager`..
│   │   │   │   │   ├── runtime/  # Каталог runtime; назначение уточняется по дочерним файлам.
│   │   │   │   │   │   ├── lifecycle/  # Каталог lifecycle; назначение уточняется по дочерним файлам.
│   │   │   │   │   │   │   ├── __init__.py  # Инициализация Python-пакета `lifecycle`.
│   │   │   │   │   │   │   ├── test_window_lifecycle_floating_safety.py  # Python-модуль: Unit-тесты floating-window safety сценариев lifecycle `DockPanelsManager`..
│   │   │   │   │   │   │   ├── test_window_lifecycle_minimize_restore.py  # Python-модуль: Unit-тесты minimize/restore сценариев lifecycle `DockPanelsManager`..
│   │   │   │   │   │   │   └── test_window_lifecycle_startup.py  # Python-модуль: Unit-тесты startup и default-layout lifecycle сценариев `DockPanelsManager`..
│   │   │   │   │   │   ├── visibility_restore/  # Каталог visibility restore; назначение уточняется по дочерним файлам.
│   │   │   │   │   │   │   ├── __init__.py  # Инициализация Python-пакета `visibility_restore`.
│   │   │   │   │   │   │   ├── test_visibility_collapse.py  # Python-модуль: Unit-тесты visibility и collapse сценариев `DockPanelsManager`..
│   │   │   │   │   │   │   ├── test_visibility_shell_phase.py  # Python-модуль: Unit-тесты compact shell-phase сценариев `DockPanelsManager`..
│   │   │   │   │   │   │   └── test_visibility_snapshot_restore.py  # Python-модуль: Unit-тесты snapshot restore сценариев visibility state `DockPanelsManager`..
│   │   │   │   │   │   ├── __init__.py  # Инициализация Python-пакета `runtime`.
│   │   │   │   │   │   └── test_dock_panels_manager_shutdown_guards.py  # Python-модуль: Unit-тесты shutdown и event-filter guardrails `DockPanelsManager`..
│   │   │   │   │   ├── splitter_geometry/  # Каталог splitter geometry; назначение уточняется по дочерним файлам.
│   │   │   │   │   │   ├── __init__.py  # Инициализация Python-пакета `splitter_geometry`.
│   │   │   │   │   │   ├── test_splitter_geometry_live_drags.py  # Python-модуль: Unit-тесты live splitter-drag сценариев geometry runtime..
│   │   │   │   │   │   ├── test_splitter_geometry_perimeter.py  # Python-модуль: Unit-тесты perimeter geometry сценариев для splitter runtime..
│   │   │   │   │   │   └── test_splitter_geometry_persistence.py  # Python-модуль: Unit-тесты snapshot и cache persistence сценариев splitter geometry..
│   │   │   │   │   ├── __init__.py  # Инициализация Python-пакета `manager`.
│   │   │   │   │   ├── _dock_panels_manager_test_helpers.py  # Python-модуль: Общие helper-функции для manager-level unit-тестов dock panels..
│   │   │   │   │   └── test_dock_panels_manager_workspace_bootstrap.py  # Python-модуль: Unit-тесты bootstrap и initial workspace assembly `DockPanelsManager`..
│   │   │   │   ├── panels/  # Каталог panels; назначение уточняется по дочерним файлам.
│   │   │   │   │   ├── contracts/  # Контракты между поверхностями и процессами.
│   │   │   │   │   │   ├── __init__.py  # Инициализация Python-пакета `contracts`.
│   │   │   │   │   │   └── test_panel_workspace_contracts.py  # Python-модуль: Unit-тесты минимальных workspace-контрактов concrete dock panel widgets..
│   │   │   │   │   ├── __init__.py  # Инициализация Python-пакета `panels`.
│   │   │   │   │   ├── _panel_test_helpers.py  # Python-модуль: Общие helper-функции для unit-тестов dock panel widgets..
│   │   │   │   │   ├── test_data_panel.py  # Python-модуль: Unit-тесты для DataPanel (C-050)..
│   │   │   │   │   ├── test_market_overview.py  # Python-модуль: Unit-тесты для Market Overview и symbol-to-chart интеграции..
│   │   │   │   │   ├── test_navigator_panel.py  # Python-модуль: Unit-тесты для NavigatorPanel и её подпанелей..
│   │   │   │   │   ├── test_strategy_tester_panel.py  # Python-модуль: Unit-тесты для StrategyTesterPanel (C-049)..
│   │   │   │   │   └── test_tools_panel.py  # Python-модуль: Unit-тесты для ToolsPanel (C-048)..
│   │   │   │   ├── __init__.py  # Инициализация Python-пакета `dock_panels`.
│   │   │   │   ├── test_base_dock_panel.py  # Python-модуль: Unit-тесты базового workspace/content контракта `BaseDockPanel`..
│   │   │   │   ├── test_panel_drag_presentation_spec.py  # Python-модуль: Unit-тесты pure spec-builder для `C-106/C-107` visual panel drag presentation..
│   │   │   │   └── test_workspace_dock_panels_adapter.py  # Python-модуль: Focused unit tests for `ui.layout.workspace.adapters.dock_panels_adapter`..
│   │   │   ├── menubar/  # Каталог menubar; назначение уточняется по дочерним файлам.
│   │   │   │   ├── sections/  # Каталог sections; назначение уточняется по дочерним файлам.
│   │   │   │   │   ├── __init__.py  # Инициализация Python-пакета `sections`.
│   │   │   │   │   ├── test_menu_sections_ai_monitoring.py  # Python-модуль: Проверить section-level контракты `AIMenuSection` и `MonitoringMenuSection`..
│   │   │   │   │   ├── test_menu_sections_core.py  # Python-модуль: Проверить базовые menu sections `File`, `Edit` и `View` для `ui.layout.menubar`..
│   │   │   │   │   └── test_menu_sections_platform_tail.py  # Python-модуль: Проверить platform/support menu sections хвоста `ui.layout.menubar`..
│   │   │   │   ├── __init__.py  # Инициализация Python-пакета `menubar`.
│   │   │   │   ├── _menu_bar_test_helpers.py  # Python-модуль: Сконцентрировать общие helper-функции для unit-тестов `ui.layout.menubar`..
│   │   │   │   ├── test_menu_bar_icons.py  # Python-модуль: Проверить icon wiring и `refresh_icons()` contracts для `MenuBar` и menu sections..
│   │   │   │   ├── test_menu_bar_shell.py  # Python-модуль: Проверить shell-, API- и style-level контракты `MenuBar`..
│   │   │   │   ├── test_menu_bar_unavailable_routing.py  # Python-модуль: Проверить menu-level контур unified unavailable-routing..
│   │   │   │   ├── test_menu_event_filter.py  # Python-модуль: Unit-тесты для MenuEventFilter (ui.theme.menu.menu_event_filter)..
│   │   │   │   └── test_menu_style.py  # Python-модуль: Unit-тесты для NoOverlapMenuStyle (ui.theme.menu.menu_style)..
│   │   │   ├── toolbar/  # Каталог toolbar; назначение уточняется по дочерним файлам.
│   │   │   │   ├── icon_provider/  # Каталог icon provider; назначение уточняется по дочерним файлам.
│   │   │   │   │   ├── __init__.py  # Инициализация Python-пакета `icon_provider`.
│   │   │   │   │   ├── _icon_provider_test_helpers.py  # Python-модуль: Собрать общие helper-функции для `IconProvider` test-slices..
│   │   │   │   │   ├── test_icon_provider_cache_theme.py  # Python-модуль: Проверить cache- и theme-related контракты `IconProvider`..
│   │   │   │   │   └── test_icon_provider_init_resolution.py  # Python-модуль: Проверить init/defaults и resolution chain для `IconProvider`..
│   │   │   │   ├── icons/  # Иконки интерфейса и ресурсные семейства.
│   │   │   │   │   ├── __init__.py  # Инициализация Python-пакета `icons`.
│   │   │   │   │   └── test_icon_pipeline.py  # Python-модуль: Unit-тесты icon pipeline — D-060..
│   │   │   │   ├── manager/  # Каталог manager; назначение уточняется по дочерним файлам.
│   │   │   │   │   ├── __init__.py  # Инициализация Python-пакета `manager`.
│   │   │   │   │   ├── test_toolbar_factory_lifecycle.py  # Python-модуль: Проверить factory-, lifecycle- и dispatch-level контракты toolbar runtime family..
│   │   │   │   │   └── test_toolbar_manager_config.py  # Python-модуль: Проверить config-, enable/disable- и idempotency-контракты `ToolBarManager`..
│   │   │   │   ├── registry/  # Каталог registry; назначение уточняется по дочерним файлам.
│   │   │   │   │   ├── __init__.py  # Инициализация Python-пакета `registry`.
│   │   │   │   │   ├── test_toolbar_registration_contracts.py  # Python-модуль: Проверить registration- и inheritance-контракты toolbar family..
│   │   │   │   │   └── test_toolbar_registry_runtime_api.py  # Python-модуль: Проверить class-level state и module-level API контракты `ToolbarRegistry`..
│   │   │   │   ├── __init__.py  # Инициализация Python-пакета `toolbar`.
│   │   │   │   ├── _toolbar_test_helpers.py  # Python-модуль: Сконцентрировать общие helper-функции и спецификации для тестов `ui.layout.toolbar`..
│   │   │   │   ├── test_toolbar_icons.py  # Python-модуль: Проверить icon wiring и `refresh_icons()` contracts для `ui.layout.toolbar`..
│   │   │   │   └── test_toolbar_sections.py  # Python-модуль: Проверить instantiation и runtime action contracts тулбаров `ui.layout.toolbar`..
│   │   │   ├── workspace/  # Каталог workspace; назначение уточняется по дочерним файлам.
│   │   │   │   ├── topology/  # Каталог topology; назначение уточняется по дочерним файлам.
│   │   │   │   │   ├── zone_tree_validation/  # Каталог zone tree validation; назначение уточняется по дочерним файлам.
│   │   │   │   │   │   ├── __init__.py  # Инициализация Python-пакета `zone_tree_validation`.
│   │   │   │   │   │   ├── test_zone_tree_constructor_guards.py  # Python-модуль: Unit-тесты constructor и public guard paths для `ZoneTree`..
│   │   │   │   │   │   ├── test_zone_tree_payload_guards.py  # Python-модуль: Unit-тесты payload shape и deserialization guards для `ZoneTree`..
│   │   │   │   │   │   └── test_zone_tree_topology_guards.py  # Python-модуль: Unit-тесты topology drift и cycle guards для `ZoneTree`..
│   │   │   │   │   ├── __init__.py  # Инициализация Python-пакета `topology`.
│   │   │   │   │   ├── _topology_test_helpers.py  # Python-модуль: Вспомогательные функции для unit-тестов `ui.layout.workspace.topology`..
│   │   │   │   │   ├── test_topology_contracts.py  # Python-модуль: Unit-тесты contract и boundary semantics для `ui.layout.workspace.topology`..
│   │   │   │   │   ├── test_zone_tree_mutations.py  # Python-модуль: Unit-тесты mutation и reorder semantics для `ZoneTree`..
│   │   │   │   │   └── test_zone_tree_nodes.py  # Python-модуль: Unit-тесты low-level node invariants для `ZoneTreeNode`..
│   │   │   │   └── __init__.py  # Инициализация Python-пакета `workspace`.
│   │   │   └── test_main_window_help_actions.py  # Python-модуль: Проверить owner-side help actions в `MainWindowChartActionsMixin`..
│   │   ├── qss_theme_symmetry/  # Каталог qss theme symmetry; назначение уточняется по дочерним файлам.
│   │   │   ├── __init__.py  # Инициализация Python-пакета `qss_theme_symmetry`.
│   │   │   ├── _qss_test_helpers.py  # Python-модуль: Вспомогательные данные и функции для QSS symmetry tests..
│   │   │   ├── test_qss_border_system.py  # Python-модуль: Unit-тесты border-system selector contract'ов для QSS themes..
│   │   │   ├── test_qss_menubar_menu_selectors.py  # Python-модуль: Unit-тесты `QMenuBar` и `QMenu` selector contract'ов для QSS themes..
│   │   │   └── test_qss_theme_symmetry_contract.py  # Python-модуль: Unit-тесты cross-theme selector symmetry для QSS themes..
│   │   ├── theme/  # Каталог theme; назначение уточняется по дочерним файлам.
│   │   │   ├── __init__.py  # Инициализация Python-пакета `theme`.
│   │   │   ├── _theme_test_helpers.py  # Python-модуль: Вспомогательные функции для theme-related unit-тестов..
│   │   │   ├── test_theme_loader.py  # Python-модуль: Unit-тесты file-loading и fallback contract'ов `ThemeLoader`..
│   │   │   ├── test_theme_manager_runtime.py  # Python-модуль: Unit-тесты runtime contract'ов `ThemeManager`..
│   │   │   └── test_theme_tooling.py  # Python-модуль: Unit-тесты tooling contract'ов для theme subsystem..
│   │   ├── ui_manager/  # Каталог ui manager; назначение уточняется по дочерним файлам.
│   │   │   ├── __init__.py  # Инициализация Python-пакета `ui_manager`.
│   │   │   ├── _ui_manager_test_helpers.py  # Python-модуль: Вспомогательные функции для `UIManager` unit-тестов..
│   │   │   ├── test_main_window_async_shutdown.py  # Python-модуль: Unit-тесты async shutdown wrapper path для `MainWindow`..
│   │   │   └── test_ui_manager_lifecycle.py  # Python-модуль: Unit-тесты lifecycle contract'ов для `UIManager`..
│   │   ├── workspace/  # Каталог workspace; назначение уточняется по дочерним файлам.
│   │   │   ├── adapters/  # Каталог adapters; назначение уточняется по дочерним файлам.
│   │   │   │   ├── __init__.py  # Инициализация Python-пакета `adapters`.
│   │   │   │   ├── test_workspace_central_content_adapter.py  # Python-модуль: Focused unit tests for `ui.layout.workspace.adapters.central_content_adapter`..
│   │   │   │   ├── test_workspace_facade.py  # Python-модуль: Focused unit tests for `ui.layout.workspace.workspace_facade`..
│   │   │   │   └── test_workspace_toolbar_adapter.py  # Python-модуль: Focused unit tests for `ui.layout.workspace.adapters.toolbar_adapter`..
│   │   │   ├── drag_drop/  # Каталог drag drop; назначение уточняется по дочерним файлам.
│   │   │   │   ├── __init__.py  # Инициализация Python-пакета `drag_drop`.
│   │   │   │   ├── _drag_drop_test_helpers.py  # Python-модуль: Вспомогательные функции для drag/drop unit-тестов workspace subsystem..
│   │   │   │   ├── test_drag_drop_resolver.py  # Python-модуль: Unit-тесты resolver и package-surface contract'ов `ui.layout.workspace.drag_drop`..
│   │   │   │   ├── test_drag_session.py  # Python-модуль: Unit-тесты state-machine contract'ов `DragSession`..
│   │   │   │   └── test_leakage_observability_helpers.py  # Python-модуль: Проверить bounded helper substrate для `D-125` leakage observability probes..
│   │   │   ├── graph/  # Каталог graph; назначение уточняется по дочерним файлам.
│   │   │   │   ├── __init__.py  # Инициализация Python-пакета `graph`.
│   │   │   │   ├── _graph_test_helpers.py  # Python-модуль: Вспомогательные функции для graph-related workspace unit-тестов..
│   │   │   │   ├── test_workspace_graph_contracts.py  # Python-модуль: Unit-тесты contract и import-boundary semantics для `ui.layout.workspace.graph`..
│   │   │   │   └── test_workspace_graph_mutations.py  # Python-модуль: Unit-тесты mutation и serialization contract'ов `ui.layout.workspace.graph`..
│   │   │   ├── persistence/  # Каталог persistence; назначение уточняется по дочерним файлам.
│   │   │   │   ├── __init__.py  # Инициализация Python-пакета `persistence`.
│   │   │   │   ├── _workspace_snapshot_test_helpers.py  # Python-модуль: Вспомогательные snapshot builders для workspace persistence tests..
│   │   │   │   ├── test_workspace_snapshot.py  # Python-модуль: Unit-тесты для canonical workspace persistence snapshot..
│   │   │   │   └── test_workspace_store.py  # Python-модуль: Unit-тесты для `WorkspaceStore`..
│   │   │   ├── runtime/  # Каталог runtime; назначение уточняется по дочерним файлам.
│   │   │   │   ├── __init__.py  # Инициализация Python-пакета `runtime`.
│   │   │   │   ├── _runtime_test_helpers.py  # Python-модуль: Вспомогательные функции для runtime-related workspace unit-тестов..
│   │   │   │   ├── test_workspace_events.py  # Python-модуль: Unit-тесты event-layer contract'ов `ui.layout.workspace.runtime`..
│   │   │   │   └── test_zone_registry.py  # Python-модуль: Unit-тесты `ZoneRegistry` и runtime import-boundary contract'ов..
│   │   │   ├── __init__.py  # Инициализация Python-пакета `workspace`.
│   │   │   ├── _workspace_loader_test_helpers.py  # Python-модуль: Вспомогательные loader-функции для workspace pure-test packages..
│   │   │   ├── test_workspace_animation_hooks.py  # Python-модуль: Focused unit tests for `ui.layout.workspace.animation` reactive contracts..
│   │   │   ├── test_workspace_package.py  # Python-модуль: Contract and structural tests for `ui.layout.workspace` package skeleton..
│   │   │   └── test_workspace_shells.py  # Python-модуль: Unit tests for workspace shell abstractions and content-host protocol..
│   │   ├── __init__.py  # Инициализация Python-пакета `ui`.
│   │   ├── conftest.py  # Python-модуль: Фикстуры для unit-тестов UI-пакета AIFE..
│   │   ├── test_base_components_package_surface.py  # Python-модуль: Проверить каноническую package-surface структуру `ui.base_components`..
│   │   ├── test_ui_package_surface.py  # Python-модуль: Проверить канонический и compatibility package surface для `ui`..
│   │   └── test_workspace_closure_matrix.py  # Python-модуль: Closure contract tests for workspace framework finalization (`C-102`)..
│   ├── validators/  # Каталог validators; назначение уточняется по дочерним файлам.
│   │   ├── verified_patch_handoff/  # Preflight/post-apply, strict path-carriers, lineage и отказные доказательства.
│   │   │   ├── conftest.py  # Общая Git/carrier factory validator-тестов.
│   │   │   ├── test_patch_content.py  # Операции patch и task ownership schema 3.
│   │   │   ├── test_preflight.py  # Exact-head, integrity и authorization boundary.
│   │   │   └── test_review_lineage.py  # Carrier/commit lineage и historical read compatibility.
│   │   ├── drift_calibration/  # Каталог drift calibration; назначение уточняется по дочерним файлам.
│   │   │   ├── __init__.py  # Инициализация Python-пакета `drift_calibration`.
│   │   │   ├── _i975_metrics.py  # Python-модуль: Зафиксировать базовую линию и ограниченные helpers сравнения для `I-975`..
│   │   │   └── test_i975_metrics.py  # Python-модуль: Проверить ограниченный контур метрик для `I-975`..
│   │   ├── drift_cli/  # Каталог drift cli; назначение уточняется по дочерним файлам.
│   │   │   └── test_validate_architectural_drift.py  # Python-модуль: Проверить CLI entry point `validate_architectural_drift.py`..
│   │   ├── drift_exceptions/  # Каталог drift exceptions; назначение уточняется по дочерним файлам.
│   │   │   ├── __init__.py  # Инициализация Python-пакета `drift_exceptions`.
│   │   │   ├── README.md  # Обзор и маршрут чтения: drift_exceptions.
│   │   │   └── test_drift_exceptions.py  # Python-модуль: Проверить exception mechanism для drift validator (`I-977`)..
│   │   ├── drift_fixtures/  # Каталог drift fixtures; назначение уточняется по дочерним файлам.
│   │   │   ├── dpt_001_authority_drift/  # Каталог dpt 001 authority drift; назначение уточняется по дочерним файлам.
│   │   │   │   ├── __init__.py  # Инициализация Python-пакета `dpt_001_authority_drift`.
│   │   │   │   ├── adapter_bridge.py  # Python-модуль: Mirror-adapter fixture module для `DPT-001`..
│   │   │   │   ├── expected_report.json  # JSON-конфигурация или данные: expected report.
│   │   │   │   └── owner_state.py  # Python-модуль: Authority-owner fixture module для `DPT-001`..
│   │   │   ├── dpt_004_indirect_execution_drift/  # Каталог dpt 004 indirect execution drift; назначение уточняется по дочерним файлам.
│   │   │   │   ├── __init__.py  # Инициализация Python-пакета `dpt_004_indirect_execution_drift`.
│   │   │   │   ├── expected_report.json  # JSON-конфигурация или данные: expected report.
│   │   │   │   ├── orchestrator_flow.py  # Python-модуль: Boundary-orchestrator fixture module для `DPT-004`..
│   │   │   │   └── projection_helper.py  # Python-модуль: Secondary collaborator для boundary-orchestrator fixture..
│   │   │   ├── __init__.py  # Инициализация Python-пакета `drift_fixtures`.
│   │   │   ├── _fixture_runner.py  # Python-модуль: Вспомогательный runner для fixture-based drift validator tests..
│   │   │   ├── dpt_004_owner_runtime.py  # Python-модуль: Cross-package owner fixture module для positive anchor `DPT-004`..
│   │   │   └── test_fixture_corpus.py  # Python-модуль: Focused proof contour для synthetic drift fixtures `I-976`..
│   │   ├── drift_model/  # Каталог drift model; назначение уточняется по дочерним файлам.
│   │   │   ├── __init__.py  # Инициализация Python-пакета `drift_model`.
│   │   │   ├── test_drift_extractor.py  # Python-модуль: Проверить живое доказательство извлечения для `_drift_model`..
│   │   │   ├── test_drift_model_types.py  # Python-модуль: Проверить неизменяемые типы модели для `_drift_model/`..
│   │   │   ├── test_entity_classifier.py  # Python-модуль: Проверить структурный классификатор сущностей для `_drift_model/`..
│   │   │   └── test_import_graph.py  # Python-модуль: Проверить AST-граф направлений импортов и эвристики обхода границ..
│   │   ├── drift_patterns/  # Каталог drift patterns; назначение уточняется по дочерним файлам.
│   │   │   ├── _reexport_fixture_pkg/  # Каталог reexport fixture pkg; назначение уточняется по дочерним файлам.
│   │   │   │   ├── __init__.py  # Инициализация Python-пакета `_reexport_fixture_pkg`.
│   │   │   │   └── base_widget.py  # Python-модуль: Minimal synthetic owner module для evaluator regression tests..
│   │   │   ├── __init__.py  # Инициализация Python-пакета `drift_patterns`.
│   │   │   ├── test_evaluator.py  # Python-модуль: Проверить evaluator для `_drift_patterns` на synthetic drift model..
│   │   │   ├── test_evaluator_live_calibration.py  # Python-модуль: Проверить live calibration boundary evaluator'а на scope `I-974` после Phase 5B..
│   │   │   ├── test_evaluator_non_ui_calibration.py  # Python-модуль: Проверить bounded non-UI calibration contour для evaluator..
│   │   │   ├── test_pattern_registry.py  # Python-модуль: Проверить YAML-driven registry для `_drift_patterns`..
│   │   │   └── test_signal_types.py  # Python-модуль: Проверить typed signal/evidence payload для `_drift_patterns`..
│   │   ├── generated_layer/  # Каталог generated layer; назначение уточняется по дочерним файлам.
│   │   │   ├── test_validate_generated_completeness.py  # Python-модуль: Проверить validator полноты generated layer для current aggregate carrier..
│   │   │   ├── test_validate_generated_continuity.py  # Python-модуль: Проверить validator truthful continuity и manual ambiguity route..
│   │   │   └── test_validate_owner_generated_sync.py  # Python-модуль: Проверка узкого validator-а `owner -> registries -> generated` для.
│   │   ├── measurement/  # Каталог measurement; назначение уточняется по дочерним файлам.
│   │   │   ├── __init__.py  # Инициализация Python-пакета `measurement`.
│   │   │   └── test_validate_owner_corpus_t0_package.py  # Python-модуль: Unit-тесты для bounded validator-а `I-1043`..
│   │   ├── owner_publication/  # Каталог owner publication; назначение уточняется по дочерним файлам.
│   │   │   ├── __init__.py  # Инициализация Python-пакета `owner_publication`.
│   │   │   └── test_validate_first_publication_completeness.py  # Python-модуль: Unit-тесты для validate_first_publication_completeness (I-1009)..
│   │   ├── semantic_catalog/  # Каталог semantic catalog; назначение уточняется по дочерним файлам.
│   │   │   └── test_validate_semantic_catalog_boundaries.py  # Python-модуль: Проверить bounded validator semantic catalog contour для `I-1036`..
│   │   ├── signal_taxonomy/  # Каталог signal taxonomy; назначение уточняется по дочерним файлам.
│   │   │   └── test_signal_taxonomy.py  # Python-модуль: Проверить shared signal taxonomy для validator-контуров..
│   │   ├── _hook_ecosystem_test_support.py  # Python-модуль: Узкие builders и YAML helper'ы для unit-тестов hook ecosystem..
│   │   ├── test_check_vestigial_markers.py  # Python-модуль: Проверить валидатор `check_vestigial_markers.py`..
│   │   ├── test_exclusions_stability.py  # Python-модуль: Тестирование стабильности списка исключений валидатора метаданных Markdown..
│   │   ├── test_validate_adr_continuity.py  # Python-модуль: Проверка валидатора ADR continuity carrier gate..
│   │   ├── test_validate_adr_registry.py  # Python-модуль: Проверка валидатора ADR_REGISTRY sync..
│   │   ├── test_validate_batch_done_evidence.py  # Python-модуль: Проверка валидатора evidence-гейта для batch Done задач..
│   │   ├── test_validate_contract_references.py  # Python-модуль: Проверка валидатора CONTRACT-* ссылок..
│   │   ├── test_validate_contract_registry.py  # Python-модуль: Проверка валидатора CONTRACTS_REGISTRY sync..
│   │   ├── test_validate_diagram_json_freshness.py  # Python-модуль: Unit-тесты для bounded `V2`-валидатора `validate_diagram_json_freshness.py`..
│   │   ├── test_validate_diagram_svg_parity.py  # Python-модуль: Unit-тесты для `V1`-валидатора `validate_diagram_svg_parity.py`..
│   │   ├── test_validate_doc_freshness.py  # Python-модуль: Unit-тесты для узкого валидатора `validate_doc_freshness.py`..
│   │   ├── test_validate_hook_coverage.py  # Python-модуль: Проверка default-inclusive coverage validator для hook ecosystem..
│   │   ├── test_validate_hook_registry_sync.py  # Python-модуль: Проверка sync-validator для `HOOK_REGISTRY`..
│   │   ├── test_validate_lint_suppressions.py  # Python-модуль: Проверить валидатор `validate_lint_suppressions.py`..
│   │   ├── test_validate_markdown_metadata.py  # Python-модуль: Unit‑тесты для валидатора `validate_markdown_metadata.py` (STD-DOC-METADATA-001)..
│   │   ├── test_validate_owner_aliases.py  # Python-модуль: Unit-тесты для валидатора `validate_owner_aliases.py`..
│   │   ├── test_validate_std_references.py  # Python-модуль: Проверка валидатора STD-* ссылок (I-018)..
│   │   ├── test_validate_structural_layout.py  # Python-модуль: Проверка валидатора structural layout quality..
│   │   ├── test_validate_structural_pressure.py  # Python-модуль: Проверка валидатора structural pressure..
│   │   ├── test_validate_test_cost_enforcement.py  # Python-модуль: Проверить валидатор `validate_test_cost_enforcement.py`..
│   │   ├── test_validate_tz_backlog_sync.py  # Python-модуль: Проверка валидатора синхронизации DEV_TZ и canonical backlog..
│   │   └── test_validate_workaround_markers.py  # Python-модуль: Проверить валидатор `validate_workaround_markers.py`..
│   ├── __init__.py  # Инициализация Python-пакета `unit`.
│   ├── test_domain_managers_smoke.py  # Python-модуль: Smoke/unit-тесты доменных менеджеров AIFE..
│   ├── test_initializer_package_surface.py  # Python-модуль: Проверить package surface корневого пакета `initializer` без открытия.
│   ├── test_main.py  # Python-модуль: Retained-root anchor suite для `main.py`..
│   └── test_system_initializer.py  # Python-модуль: Retained-root anchor suite для `SystemInitializer`..
├── __init__.py  # Инициализация Python-пакета `tests`.
├── conftest.py  # Python-модуль: Настройка окружения для запуска тестов `pytest` в проекте AIFE..
└── README.md  # Обзор и маршрут чтения: Тесты проекта AIFE.
```

## Правило чтения

Комментарии рядом с файлами дают короткую тематическую роль. Подробное поведение проверяется по коду, тестам и профильным документам.
