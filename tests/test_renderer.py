import pytest

from ai_docgen.renderer import DocumentRenderer, TemplateLoader

SAMPLE_DOC = """# My Service

Some intro text.

<!-- AUTO:overview -->
Old overview content.
<!-- /AUTO:overview -->

<!-- MANUAL -->
Manual section — never touch this.
<!-- /MANUAL -->

<!-- AUTO:getting_started -->
Old getting started.
<!-- /AUTO:getting_started -->
"""


def test_parse_sections_finds_auto() -> None:
    renderer = DocumentRenderer()
    sections = renderer.parse_sections(SAMPLE_DOC)
    auto_names = [s.name for s in sections if s.is_auto]
    assert "overview" in auto_names
    assert "getting_started" in auto_names


def test_parse_sections_finds_manual() -> None:
    renderer = DocumentRenderer()
    sections = renderer.parse_sections(SAMPLE_DOC)
    manual_sections = [s for s in sections if not s.is_auto and s.name == "MANUAL"]
    assert len(manual_sections) == 1


def test_patch_section_replaces_content() -> None:
    renderer = DocumentRenderer()
    result = renderer.patch_section(SAMPLE_DOC, "overview", "New overview content.\n")
    assert "New overview content." in result
    assert "Old overview content." not in result


def test_patch_section_preserves_manual() -> None:
    renderer = DocumentRenderer()
    result = renderer.patch_section(SAMPLE_DOC, "overview", "New overview.\n")
    assert "Manual section — never touch this." in result


def test_patch_section_preserves_other_auto() -> None:
    renderer = DocumentRenderer()
    result = renderer.patch_section(SAMPLE_DOC, "overview", "New overview.\n")
    assert "Old getting started." in result


def test_patch_nonexistent_section_returns_unchanged() -> None:
    renderer = DocumentRenderer()
    result = renderer.patch_section(SAMPLE_DOC, "nonexistent", "New content.\n")
    assert result == SAMPLE_DOC


def test_auto_section_names() -> None:
    renderer = DocumentRenderer()
    names = renderer.auto_section_names(SAMPLE_DOC)
    assert names == ["overview", "getting_started"]


def test_load_builtin_readme_template() -> None:
    loader = TemplateLoader(source="builtin")
    content = loader.load("readme/default")
    assert "AUTO:overview" in content
    assert "AUTO:getting_started" in content


def test_load_missing_template_raises() -> None:
    loader = TemplateLoader(source="builtin")
    with pytest.raises(FileNotFoundError):
        loader.load("readme/nonexistent")


def test_render_template_with_context() -> None:
    loader = TemplateLoader(source="builtin")
    result = loader.render("readme/default", {"service_name": "my-service"})
    assert "# my-service" in result
