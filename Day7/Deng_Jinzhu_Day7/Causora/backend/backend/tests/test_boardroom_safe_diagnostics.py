import logging
from types import SimpleNamespace
from app import boardroom_adapter as adapter


def test_role_failure_logs_only_safe_codes(caplog):
    failure = SimpleNamespace(reason="roles_incomplete", status=503, details={
        "failureReasons": {"CFO": "role_option_coverage_incomplete", "COO": "secret text", "unknown": "provider_unavailable"},
        "prompt": "private prompt",
    })
    with caplog.at_level(logging.WARNING):
        result = adapter._pipeline_error(failure)
    assert result.reason == "roles_incomplete"
    assert "role_option_coverage_incomplete" in caplog.text
    assert "secret text" not in caplog.text
    assert "private prompt" not in caplog.text
    assert "unknown" not in caplog.text
