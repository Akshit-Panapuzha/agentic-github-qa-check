import fnmatch
from typing import List

from github import Github

from qa.config import Config
from qa.linter import lint_file
from qa.models import Finding


def is_ignored(filename: str, ignore_paths: List[str]) -> bool:
    return any(fnmatch.fnmatch(filename, pattern) for pattern in ignore_paths)


def run(
    github_token: str,
    repo_name: str,
    pr_number: int,
    head_sha: str,
    config: Config,
    pylintrc: str = None,
) -> List[Finding]:
    g = Github(github_token)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)

    all_findings: List[Finding] = []

    for f in pr.get_files():
        if not f.filename.endswith(".py"):
            continue
        if is_ignored(f.filename, config.ignore_paths):
            continue
        if not f.patch:
            continue
        try:
            content = repo.get_contents(f.filename, ref=head_sha).decoded_content.decode("utf-8")
        except Exception:
            continue
        all_findings.extend(lint_file(f.filename, content, pylintrc))

    return all_findings
