from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import yaml


@dataclass
class Config:
    severity_filter: List[str] = field(default_factory=lambda: ["critical", "medium"])
    max_comments_per_pr: int = 20
    ignore_paths: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=lambda: ["python"])


def load_config(repo_root: str = ".") -> Config:
    qa_yaml = Path(repo_root) / ".qa.yaml"
    if not qa_yaml.exists():
        return Config()
    try:
        with open(qa_yaml) as f:
            data = yaml.safe_load(f)
        qa = (data or {}).get("qa", {}) or {}
        config = Config()
        if "severity_filter" in qa:
            config.severity_filter = qa["severity_filter"]
        if "max_comments_per_pr" in qa:
            config.max_comments_per_pr = qa["max_comments_per_pr"]
        if "ignore_paths" in qa:
            config.ignore_paths = qa["ignore_paths"]
        if "languages" in qa:
            config.languages = qa["languages"]
        return config
    except Exception:
        return Config()
