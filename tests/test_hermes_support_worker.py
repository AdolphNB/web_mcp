import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace


spec = importlib.util.spec_from_file_location("support_worker", Path(__file__).parents[1] / "integrations/hermes/support_worker.py")
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)


def test_child_environment_does_not_inherit_management_credentials(monkeypatch, tmp_path):
    monkeypatch.setenv("SITE_ADMIN_TOKEN", "private-admin")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "private-personal-key")
    monkeypatch.setenv("HERMES_HOME", "personal-home")
    captured = {}

    def run(args, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(stdout='informational log\nSUPPORT_RESULT=' + json.dumps({"success": True, "answer": "reply"}))

    monkeypatch.setattr(worker.subprocess, "run", run)
    result = worker.run_agent({"messages": []}, {"profile": str(tmp_path), "hermes_python": "python"})
    assert result == {"success": True, "answer": "reply"}
    assert "SITE_ADMIN_TOKEN" not in captured["env"]
    assert "DEEPSEEK_API_KEY" not in captured["env"]
    assert captured["env"]["HERMES_HOME"] == str(tmp_path)
    assert captured["cwd"] == str(tmp_path)
    assert captured["timeout"] == 100


def test_unstructured_provider_failure_never_becomes_visitor_reply(monkeypatch, tmp_path):
    monkeypatch.setattr(worker.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(stdout="provider-error: private-key"))
    result = worker.run_agent({}, {"profile": str(tmp_path), "hermes_python": "python"})
    assert result == {"success": False, "answer": ""}
