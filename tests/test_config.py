import os
import tempfile
import textwrap

from qa.config import Config, load_config


def test_default_config_when_no_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg = load_config(tmpdir)
    assert cfg.severity_filter == ["critical", "medium"]
    assert cfg.max_comments_per_pr == 20
    assert cfg.ignore_paths == []
    assert cfg.languages == ["python"]


def test_loads_qa_yaml_overrides():
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, ".qa.yaml"), "w") as f:
            f.write(textwrap.dedent("""\
                qa:
                  max_comments_per_pr: 5
                  ignore_paths:
                    - "migrations/*"
            """))
        cfg = load_config(tmpdir)
    assert cfg.max_comments_per_pr == 5
    assert cfg.ignore_paths == ["migrations/*"]
    assert cfg.severity_filter == ["critical", "medium"]  # unchanged default


def test_invalid_yaml_falls_back_to_defaults():
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, ".qa.yaml"), "w") as f:
            f.write("{ invalid yaml :")
        cfg = load_config(tmpdir)
    assert cfg.severity_filter == ["critical", "medium"]
    assert cfg.max_comments_per_pr == 20
