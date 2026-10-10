from types import SimpleNamespace
import pytest
from app import boardroom_adapter as adapter

def test_provider_factory_runtime_error_is_a_sanitized_retryable_api_failure(monkeypatch):
    class MissingDedicatedKey(RuntimeError): pass
    def factory(): raise MissingDedicatedKey('private diagnostic must not reach the browser')
    modules = {
        'agent_day4.provider': SimpleNamespace(providers_from_env=factory),
        'agent_day4.wire': SimpleNamespace(),
    }
    monkeypatch.setattr(adapter, '_ensure_agent_package_on_path', lambda: None)
    monkeypatch.setattr(adapter.importlib, 'import_module', lambda name: modules[name])
    with pytest.raises(adapter.BoardroomAdapterError) as raised:
        adapter._load_formal_runtime(object)
    error = raised.value
    assert error.status == 503
    assert error.reason == 'provider_unavailable'
    response = adapter._failure(error, 'req-config-failure')
    assert response.status_code == 503
    assert b'private diagnostic' not in response.body
    assert b'provider_unavailable' in response.body
