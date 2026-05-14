from ai_docgen.analyzer import DiffAnalyzer


def make_diff(files: list[str]) -> str:
    lines = []
    for f in files:
        lines.append(f"diff --git a/{f} b/{f}")
        lines.append(f"--- a/{f}")
        lines.append(f"+++ b/{f}")
        lines.append("@@ -1,3 +1,4 @@")
        lines.append("+new line")
    return "\n".join(lines)


def test_extract_changed_files_from_diff() -> None:
    diff = make_diff(["app/models.py", "app/services.py"])
    analyzer = DiffAnalyzer(diff_text=diff, trigger_paths=["app/**"], ignore_paths=[])
    files = analyzer.changed_files()
    assert len(files) == 2
    assert any(f.path == "app/models.py" for f in files)


def test_has_relevant_changes_matches_glob() -> None:
    diff = make_diff(["app/models.py"])
    analyzer = DiffAnalyzer(diff_text=diff, trigger_paths=["app/**"], ignore_paths=[])
    assert analyzer.has_relevant_changes() is True


def test_has_relevant_changes_ignores_excluded() -> None:
    diff = make_diff(["tests/test_models.py"])
    analyzer = DiffAnalyzer(diff_text=diff, trigger_paths=["app/**"], ignore_paths=["tests/**"])
    assert analyzer.has_relevant_changes() is False


def test_has_relevant_changes_no_trigger_match() -> None:
    diff = make_diff(["docs/README.md"])
    analyzer = DiffAnalyzer(diff_text=diff, trigger_paths=["app/**"], ignore_paths=[])
    assert analyzer.has_relevant_changes() is False


def test_empty_diff_no_relevant_changes() -> None:
    analyzer = DiffAnalyzer(diff_text="", trigger_paths=["app/**"], ignore_paths=[])
    assert analyzer.has_relevant_changes() is False


def test_diff_summary_for_prompt() -> None:
    diff = make_diff(["app/models.py"])
    analyzer = DiffAnalyzer(diff_text=diff, trigger_paths=["app/**"], ignore_paths=[])
    summary = analyzer.diff_summary()
    assert "app/models.py" in summary
