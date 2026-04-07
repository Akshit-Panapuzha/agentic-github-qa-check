import re
from typing import Dict, List, Optional

from github import GithubException

from qa.config import Config
from qa.models import Finding


def parse_diff_positions(patch: str) -> Dict[int, int]:
    """Map new-file line numbers to 1-indexed diff positions."""
    positions: Dict[int, int] = {}
    diff_pos = 0
    current_new_line = 0

    for line in patch.split("\n"):
        if not line:
            continue
        if line.startswith("@@"):
            diff_pos += 1
            match = re.search(r"\+(\d+)", line)
            if match:
                current_new_line = int(match.group(1)) - 1
        elif line.startswith("+"):
            diff_pos += 1
            current_new_line += 1
            positions[current_new_line] = diff_pos
        elif line.startswith("-"):
            diff_pos += 1
        elif line.startswith("\\"):
            pass  # "\ No newline at end of file"
        else:
            diff_pos += 1
            current_new_line += 1
            positions[current_new_line] = diff_pos

    return positions


def snap_to_diff(line_number: int, positions: Dict[int, int]) -> Optional[int]:
    """Return the diff position for the nearest file line. None if positions is empty."""
    if not positions:
        return None
    if line_number in positions:
        return positions[line_number]
    nearest = min(positions.keys(), key=lambda x: abs(x - line_number))
    return positions[nearest]


def build_summary(findings: List[Finding]) -> str:
    if not findings:
        return "**QA Lint Check passed.** No issues found."

    counts: Dict[str, int] = {}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1

    total = sum(counts.values())
    parts = [f"{v} {k}" for k, v in counts.items() if v > 0]
    lines = [f"**QA Lint Check found {total} issue(s):** {', '.join(parts)}."]

    low_findings = [f for f in findings if f.severity == "low"]
    if low_findings:
        lines += [
            "",
            "<details>",
            f"<summary>Low severity findings ({len(low_findings)})</summary>",
            "",
        ]
        for f in low_findings:
            lines.append(f"**{f.filename}:{f.line_number}** — {f.title}")
            lines.append(f"_{f.explanation}_")
            lines.append("")
        lines.append("</details>")

    return "\n".join(lines)


def post_review(repo, pr_number: int, findings: List[Finding], config: Config) -> None:
    pr = repo.get_pull(pr_number)
    file_patches = {f.filename: f.patch for f in pr.get_files() if f.patch}

    inline_findings = [
        f for f in findings if f.severity in config.severity_filter
    ][: config.max_comments_per_pr]

    if inline_findings:
        comments = []
        for finding in inline_findings:
            positions = parse_diff_positions(file_patches.get(finding.filename, ""))
            position = snap_to_diff(finding.line_number, positions)
            if position is None:
                continue
            body = f"**[{finding.severity.upper()}] {finding.title}**\n\n{finding.explanation}"
            comments.append({"path": finding.filename, "position": position, "body": body})

        if comments:
            try:
                pr.create_review(body="", event="COMMENT", comments=comments)
            except GithubException as e:
                print(f"Warning: could not post inline review (HTTP {e.status}): {e.data}")

    pr.create_issue_comment(build_summary(findings))
