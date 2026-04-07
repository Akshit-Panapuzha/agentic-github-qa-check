from qa.models import Finding


def test_finding_stores_all_fields():
    f = Finding(
        filename="app/models.py",
        line_number=10,
        severity="critical",
        title="[E0602] undefined-variable",
        explanation="Undefined variable 'foo'",
        suggestion="",
    )
    assert f.filename == "app/models.py"
    assert f.line_number == 10
    assert f.severity == "critical"
    assert f.title == "[E0602] undefined-variable"
    assert f.explanation == "Undefined variable 'foo'"
    assert f.suggestion == ""


def test_finding_equality():
    f1 = Finding("a.py", 1, "medium", "title", "exp", "sug")
    f2 = Finding("a.py", 1, "medium", "title", "exp", "sug")
    assert f1 == f2
