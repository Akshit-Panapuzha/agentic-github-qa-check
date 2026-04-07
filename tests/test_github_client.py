from unittest.mock import MagicMock, patch

from qa.config import Config
from qa.github_client import build_summary, parse_diff_positions, post_review, snap_to_diff
from qa.models import Finding


# --- parse_diff_positions ---

def test_parse_diff_positions_maps_lines_to_diff_positions():
    diff_str = "@@ -1,2 +1,3 @@\n line1\n+added\n line2"
    positions = parse_diff_positions(diff_str)
    # @@ = diff pos 1
    # " line1" = new file line 1, diff pos 2
    # "+added" = new file line 2, diff pos 3
    # " line2" = new file line 3, diff pos 4
    assert positions[1] == 2
    assert positions[2] == 3
    assert positions[3] == 4


def test_parse_diff_positions_removed_lines_not_in_map():
    diff_str = "@@ -1,2 +1,1 @@\n context\n-removed"
    positions = parse_diff_positions(diff_str)
    assert 1 in positions
    assert 2 not in positions


def test_parse_diff_positions_empty_returns_empty():
    assert parse_diff_positions("") == {}


# --- snap_to_diff ---

def test_snap_to_diff_exact_match():
    positions = {1: 2, 2: 3, 3: 4}
    assert snap_to_diff(2, positions) == 3


def test_snap_to_diff_snaps_to_nearest():
    positions = {1: 2, 5: 6}
    result = snap_to_diff(3, positions)
    assert result in (2, 6)  # line 3 is equidistant from lines 1 and 5


def test_snap_to_diff_empty_positions_returns_none():
    assert snap_to_diff(5, {}) is None


# --- build_summary ---

def test_build_summary_includes_counts_and_details_block():
    findings = [
        Finding("a.py", 1, "critical", "[E0602] undefined-variable", "Undefined 'x'", ""),
        Finding("a.py", 2, "medium", "[W0611] unused-import", "Unused import os", ""),
        Finding("a.py", 3, "low", "[C0301] line-too-long", "Line too long", ""),
    ]
    summary = build_summary(findings)
    assert "critical" in summary.lower()
    assert "medium" in summary.lower()
    assert "<details>" in summary
    assert "C0301" in summary


def test_build_summary_omits_details_block_when_no_low_findings():
    findings = [Finding("a.py", 1, "critical", "[E0602] err", "bad", "")]
    summary = build_summary(findings)
    assert "<details>" not in summary


def test_build_summary_clean_message_when_no_findings():
    summary = build_summary([])
    assert summary
    assert "<details>" not in summary


# --- post_review ---

def _make_mock_repo(patch_str="@@ -1,3 +1,3 @@\n line1\n line2\n line3"):
    mock_file = MagicMock()
    mock_file.filename = "a.py"
    mock_file.patch = patch_str
    mock_pr = MagicMock()
    mock_pr.get_files.return_value = [mock_file]
    mock_repo = MagicMock()
    mock_repo.get_pull.return_value = mock_pr
    return mock_repo, mock_pr


def test_post_review_creates_inline_review_for_critical_and_medium():
    mock_repo, mock_pr = _make_mock_repo()
    findings = [
        Finding("a.py", 1, "critical", "[E0602] err", "bad", ""),
        Finding("a.py", 2, "medium", "[W0611] warn", "meh", ""),
        Finding("a.py", 3, "low", "[C0301] low", "style", ""),
    ]
    post_review(mock_repo, 1, findings, Config())
    mock_pr.create_review.assert_called_once()
    comments = mock_pr.create_review.call_args.kwargs["comments"]
    assert len(comments) == 2
    mock_pr.create_issue_comment.assert_called_once()


def test_post_review_skips_create_review_when_only_low_findings():
    mock_repo, mock_pr = _make_mock_repo()
    findings = [Finding("a.py", 1, "low", "[C0301] low", "style", "")]
    post_review(mock_repo, 1, findings, Config())
    mock_pr.create_review.assert_not_called()
    mock_pr.create_issue_comment.assert_called_once()


def test_post_review_respects_max_comments_per_pr():
    mock_repo, mock_pr = _make_mock_repo(
        "@@ -1,5 +1,5 @@\n line1\n line2\n line3\n line4\n line5"
    )
    findings = [Finding("a.py", i, "critical", f"[E{i:04d}] err", "bad", "") for i in range(1, 6)]
    post_review(mock_repo, 1, findings, Config(max_comments_per_pr=2))
    comments = mock_pr.create_review.call_args.kwargs["comments"]
    assert len(comments) == 2


def test_post_review_handles_422_gracefully():
    from github import GithubException
    mock_repo, mock_pr = _make_mock_repo()
    mock_pr.create_review.side_effect = GithubException(422, "Validation Failed", None)
    findings = [Finding("a.py", 1, "critical", "[E0602] err", "bad", "")]
    post_review(mock_repo, 1, findings, Config())  # must not raise
    mock_pr.create_issue_comment.assert_called_once()
