from unittest.mock import MagicMock, patch

from qa.config import Config
from qa.models import Finding
from qa.orchestrator import is_ignored, run


def test_is_ignored_matches_wildcard():
    assert is_ignored("migrations/0001_initial.py", ["migrations/*"]) is True


def test_is_ignored_no_match():
    assert is_ignored("app/models.py", ["migrations/*"]) is False


def test_is_ignored_empty_patterns():
    assert is_ignored("anything.py", []) is False


def _make_mock_repo(files, file_contents):
    mock_pr = MagicMock()
    mock_pr.get_files.return_value = files
    mock_repo = MagicMock()
    mock_repo.get_pull.return_value = mock_pr
    mock_repo.get_contents.side_effect = lambda path, ref: file_contents[path]
    return mock_repo


def test_run_returns_findings_for_py_files():
    mock_file = MagicMock()
    mock_file.filename = "app/models.py"
    mock_file.patch = "@@ -1,1 +1,2 @@\n line1\n+new line\n"

    mock_content = MagicMock()
    mock_content.decoded_content = b"x = foo\n"

    mock_repo = _make_mock_repo([mock_file], {"app/models.py": mock_content})
    expected = Finding("app/models.py", 1, "critical", "[E0602] err", "bad", "")

    with patch("qa.orchestrator.Github") as MockGithub, \
         patch("qa.orchestrator.lint_file", return_value=[expected]):
        MockGithub.return_value.get_repo.return_value = mock_repo
        findings = run("token", "owner/repo", 42, "def456", Config())

    assert findings == [expected]


def test_run_skips_non_py_files():
    mock_file = MagicMock()
    mock_file.filename = "README.md"
    mock_file.patch = "@@ -1 +1 @@\n+# Title\n"

    mock_repo = _make_mock_repo([mock_file], {})

    with patch("qa.orchestrator.Github") as MockGithub, \
         patch("qa.orchestrator.lint_file") as mock_lint:
        MockGithub.return_value.get_repo.return_value = mock_repo
        findings = run("token", "owner/repo", 42, "def456", Config())

    mock_lint.assert_not_called()
    assert findings == []


def test_run_skips_ignored_paths():
    mock_file = MagicMock()
    mock_file.filename = "migrations/0001.py"
    mock_file.patch = "@@ -1 +1 @@\n+x = 1\n"

    mock_repo = _make_mock_repo([mock_file], {})

    with patch("qa.orchestrator.Github") as MockGithub, \
         patch("qa.orchestrator.lint_file") as mock_lint:
        MockGithub.return_value.get_repo.return_value = mock_repo
        findings = run("token", "owner/repo", 42, "def456", Config(ignore_paths=["migrations/*"]))

    mock_lint.assert_not_called()
    assert findings == []


def test_run_skips_files_with_no_patch():
    mock_file = MagicMock()
    mock_file.filename = "app/models.py"
    mock_file.patch = None

    mock_repo = _make_mock_repo([mock_file], {})

    with patch("qa.orchestrator.Github") as MockGithub, \
         patch("qa.orchestrator.lint_file") as mock_lint:
        MockGithub.return_value.get_repo.return_value = mock_repo
        findings = run("token", "owner/repo", 42, "def456", Config())

    mock_lint.assert_not_called()
