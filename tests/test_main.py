import pytest
from unittest.mock import patch

from qa.main import main
from qa.models import Finding


def test_main_exits_1_when_findings(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "token123")
    monkeypatch.setenv("PR_NUMBER", "42")
    monkeypatch.setenv("REPO", "owner/repo")
    monkeypatch.setenv("BASE_SHA", "abc")
    monkeypatch.setenv("HEAD_SHA", "def")

    mock_finding = Finding("a.py", 1, "critical", "[E0602] err", "bad code", "")

    with patch("qa.main.orchestrator.run", return_value=[mock_finding]), \
         patch("qa.main.Github"), \
         patch("qa.main.github_client.post_review"):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1


def test_main_exits_0_when_no_findings(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "token123")
    monkeypatch.setenv("PR_NUMBER", "42")
    monkeypatch.setenv("REPO", "owner/repo")
    monkeypatch.setenv("BASE_SHA", "abc")
    monkeypatch.setenv("HEAD_SHA", "def")

    with patch("qa.main.orchestrator.run", return_value=[]), \
         patch("qa.main.Github"), \
         patch("qa.main.github_client.post_review"):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0


def test_main_passes_correct_args_to_orchestrator(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "mytoken")
    monkeypatch.setenv("PR_NUMBER", "7")
    monkeypatch.setenv("REPO", "acme/myrepo")
    monkeypatch.setenv("BASE_SHA", "base123")
    monkeypatch.setenv("HEAD_SHA", "head456")

    with patch("qa.main.orchestrator.run", return_value=[]) as mock_run, \
         patch("qa.main.Github"), \
         patch("qa.main.github_client.post_review"):
        try:
            main()
        except SystemExit:
            pass

    args = mock_run.call_args.args
    assert args[0] == "mytoken"
    assert args[1] == "acme/myrepo"
    assert args[2] == 7
    assert args[3] == "head456"
