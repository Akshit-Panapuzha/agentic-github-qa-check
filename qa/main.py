import os
import sys

from github import Github

from qa import github_client, orchestrator
from qa.config import load_config


def main() -> None:
    token = os.environ["GITHUB_TOKEN"]
    pr_number = int(os.environ["PR_NUMBER"])
    repo_name = os.environ["REPO"]
    head_sha = os.environ["HEAD_SHA"]

    config = load_config(".")
    findings = orchestrator.run(token, repo_name, pr_number, head_sha, config)

    g = Github(token)
    repo = g.get_repo(repo_name)
    github_client.post_review(repo, pr_number, findings, config)

    sys.exit(1 if findings else 0)


if __name__ == "__main__":
    main()
