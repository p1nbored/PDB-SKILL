"""Command-line entry point and plugin user-config handling."""
from __future__ import annotations

import json

import fitz
import pytest
from PIL import Image

import map_integration
import pdb_gen

PDF, MD = "PDB_2026-04-18.pdf", "PDB_2026-04-18.md"


@pytest.fixture
def fake_maps(monkeypatch):
    """Stand-in for cia-map-gen that writes a small PNG where asked."""
    def _render(prompt, out, title=None, no_header=True):
        out.parent.mkdir(parents=True, exist_ok=True)
        Image.new("L", (85, 110), 200).save(out)
        return out

    monkeypatch.setattr(pdb_gen, "generate_map", _render)


def test_default_writes_only_the_pdf(tmp_path, sample_path, fake_maps):
    rc = pdb_gen.main(["--content", str(sample_path), "--out-dir", str(tmp_path)])
    assert rc == 0
    assert sorted(p.name for p in tmp_path.iterdir()) == [PDF]


def test_maps_are_embedded_in_the_pdf(tmp_path, sample_path, fake_maps):
    pdb_gen.main(["--content", str(sample_path), "--out-dir", str(tmp_path)])
    doc = fitz.open(tmp_path / PDF)
    assert sum(len(page.get_images()) for page in doc) >= 6


def test_maps_dir_keeps_the_map_images(tmp_path, sample_path, fake_maps):
    keep = tmp_path / "plates"
    rc = pdb_gen.main(["--content", str(sample_path), "--out-dir", str(tmp_path / "out"),
                       "--maps-dir", str(keep)])
    assert rc == 0
    assert len(list(keep.glob("*.png"))) == 6
    assert sorted(p.name for p in (tmp_path / "out").iterdir()) == [PDF]


def test_format_markdown_writes_obsidian_md_with_its_maps(tmp_path, sample_path,
                                                          fake_maps):
    rc = pdb_gen.main(["--content", str(sample_path), "--out-dir", str(tmp_path),
                       "--format", "markdown"])
    assert rc == 0
    md = (tmp_path / MD).read_text(encoding="utf-8")
    assert md.startswith("---\n")
    assert not (tmp_path / PDF).exists()
    assert len(list((tmp_path / "maps").glob("*.png"))) == 6


def test_format_both_writes_pdf_and_markdown(tmp_path, sample_path, fake_maps):
    rc = pdb_gen.main(["--content", str(sample_path), "--out-dir", str(tmp_path),
                       "--format", "both", "--md-flavor", "gfm"])
    assert rc == 0
    assert (tmp_path / PDF).exists()
    md = (tmp_path / MD).read_text(encoding="utf-8")
    assert "*(Page 1)*" in md and not md.startswith("---\n")


def test_unexpanded_user_config_falls_back_to_defaults(tmp_path, sample_path,
                                                        monkeypatch, capsys):
    monkeypatch.setattr(pdb_gen, "DEFAULT_OUT_DIR", tmp_path / "default")
    rc = pdb_gen.main(["--content", str(sample_path), "--no-maps",
                       "--out-dir", "${user_config.output_dir}",
                       "--format", "${user_config.output_format}"])
    assert rc == 0
    assert sorted(p.name for p in (tmp_path / "default").iterdir()) == [PDF]
    assert "PDF written" in capsys.readouterr().out


def test_missing_content_file_exits_2(tmp_path):
    assert pdb_gen.main(["--content", str(tmp_path / "nope.json"),
                         "--out-dir", str(tmp_path)]) == 2


def test_invalid_content_exits_2(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"date": "2026-04-18", "articles": []}), encoding="utf-8")
    assert pdb_gen.main(["--content", str(bad), "--out-dir", str(tmp_path)]) == 2


def test_unknown_format_is_a_usage_error(tmp_path, sample_path):
    with pytest.raises(SystemExit) as exc:
        pdb_gen.main(["--content", str(sample_path), "--format", "docx"])
    assert exc.value.code == 2


def test_strict_maps_exit_3_when_map_fails(tmp_path, sample_path, monkeypatch):
    monkeypatch.setattr(pdb_gen, "generate_map", lambda *a, **k: None)
    rc = pdb_gen.main(["--content", str(sample_path), "--out-dir", str(tmp_path),
                       "--strict-maps"])
    assert rc == 3


@pytest.mark.parametrize("error", [PermissionError("PDF is open in a viewer"),
                                   ValueError("path on another drive")])
def test_output_failures_exit_5_without_traceback(tmp_path, sample_path, monkeypatch,
                                                  capsys, error):
    def _fail(*args, **kwargs):
        raise error

    monkeypatch.setattr(pdb_gen, "build_pdf", _fail)
    rc = pdb_gen.main(["--content", str(sample_path), "--out-dir", str(tmp_path),
                       "--no-maps"])
    assert rc == 5
    assert "error:" in capsys.readouterr().err


def test_layout_error_exits_5(tmp_path, sample_path, monkeypatch):
    from reportlab.platypus.doctemplate import LayoutError  # noqa: PLC0415

    def _fail(*args, **kwargs):
        raise LayoutError("flowable too large")

    monkeypatch.setattr(pdb_gen, "build_pdf", _fail)
    assert pdb_gen.main(["--content", str(sample_path), "--out-dir", str(tmp_path),
                         "--no-maps"]) == 5


def test_map_subprocess_output_decoded_as_utf8(tmp_path, monkeypatch):
    seen = {}

    class _Done:
        returncode = 1
        stderr = "未找到"

    def _run(cmd, **kwargs):
        seen.update(kwargs)
        return _Done()

    monkeypatch.setattr(map_integration.subprocess, "run", _run)
    assert map_integration.generate_map("Atlantis", tmp_path / "x.png") is None
    assert seen["encoding"] == "utf-8" and seen["errors"] == "replace"


def test_map_gen_located_in_sibling_skill():
    script = map_integration.find_cia_map_gen()
    assert script is not None
    assert script.name == "cia_map_gen.py"
    assert script.parent.name == "scripts"


def test_generate_map_returns_none_on_failure(tmp_path, monkeypatch):
    class _Failed:
        returncode = 2
        stderr = "no match"

    monkeypatch.setattr(map_integration.subprocess, "run", lambda *a, **k: _Failed())
    assert map_integration.generate_map("Atlantis", tmp_path / "x.png") is None
