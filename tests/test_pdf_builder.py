"""Layout invariants of the PDF replica, checked against the 1975-76 originals."""
from __future__ import annotations

import fitz
import pytest
from PIL import Image

from content_schema import brief_from_dict
from pdf_builder import build_pdf
import styles as S

BANNER = "FOR THE PRESIDENT ONLY"


@pytest.fixture(scope="module")
def built(tmp_path_factory, request):
    brief_dict = request.getfixturevalue("brief_dict_module")
    tmp = tmp_path_factory.mktemp("pdf")
    plate = tmp / "plate.png"
    Image.new("L", (850, 1100), 255).save(plate)
    brief = brief_from_dict(brief_dict)
    out = tmp / "PDB.pdf"
    labels = build_pdf(brief, out, article_maps={0: plate}, annex_map=plate)
    doc = fitz.open(out)
    pages = [p.get_text() for p in doc]
    return brief, labels, doc, pages


@pytest.fixture(scope="module")
def brief_dict_module():
    from conftest import _CN, _EN, _article  # noqa: PLC0415
    return {
        "date": "2026-04-18",
        "articles": [
            _article("Middle East", 4),
            _article("Russia-Ukraine", 3, body_en=[_EN, "[REDACTED:3]", _EN],
                     body_cn=[_CN, "[REDACTED:3]", _CN]),
            _article("Taiwan Strait", 5),
        ],
        "notes": [
            {"region": "Poland", "text_en": _EN, "text_cn": _CN,
             "summary_en": "Poland's coalition talks have stalled.",
             "summary_cn": "波兰联合政府谈判陷入停滞。"},
            {"region": "Venezuela", "text_en": _EN, "text_cn": _CN},
        ],
        "annex": {"title_en": "Iran after the ceasefire", "title_cn": "停火之后的伊朗",
                  "summary_en": "The ceasefire has bought time.",
                  "summary_cn": "停火赢得了时间。",
                  "body_en": [_EN] * 9, "body_cn": [_CN] * 9},
    }


def _body_label(text: str) -> str | None:
    """The bare page label set above the bottom banner, if any."""
    if BANNER not in text:
        return None  # cover copy number, plates, back cover
    for line in text.splitlines():
        token = line.strip()
        if token.isdigit() or (token.startswith("A") and token[1:].isdigit()):
            return token
    return None


def test_front_matter_order(built):
    _, _, _, pages = built
    assert "The President’s Daily Brief" in pages[0]
    assert "Exempt from general" in pages[1]
    assert "Table of Contents" in pages[2]
    assert "April 18, 2026" in pages[2]


def test_toc_references_resolved_pages(built):
    _, labels, _, pages = built
    toc = pages[2]
    assert f"(Page {labels['article:0']})" in toc
    assert "At Annex we discuss" in toc.replace("\n", " ")
    assert f"follows Page {labels['article_end:0']}" in toc


def test_text_pages_carry_top_and_bottom_banner(built):
    _, _, _, pages = built
    text_pages = [t for t in pages[2:-1] if _body_label(t) or "Table of Contents" in t]
    assert text_pages
    for text in text_pages:
        assert text.count(BANNER) == 2


def test_continued_on_every_page_but_section_ends(built):
    _, labels, _, pages = built
    numbered = [(t, _body_label(t)) for t in pages if _body_label(t)]
    body = [t for t, lab in numbered if lab.isdigit()]
    annex = [t for t, lab in numbered if lab.startswith("A")]
    assert len(body) >= 3 and len(annex) >= 2
    for section in (body, annex):
        assert all("--continued" in t for t in section[:-1])
        assert "--continued" not in section[-1]


def test_articles_flow_without_forced_breaks(built):
    brief, labels, _, _ = built
    # Three articles of this size share pages: the second starts on the
    # page where the first ends (the separator flows on, as in 1976).
    assert labels["article:1"] in (labels["article_end:0"],
                                   str(int(labels["article_end:0"]) + 1))
    assert len(brief.articles) == 3


def test_right_column_has_typewriter_measure(built):
    _, labels, doc, _ = built
    page = doc[3]  # first body page
    right_x0 = S.RIGHT_COL_X - 1
    lengths = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            spans = line["spans"]
            if not spans or "Plex" not in spans[0]["font"]:
                continue
            if line["bbox"][0] >= right_x0:
                lengths.append(len("".join(s["text"] for s in spans).rstrip()))
    assert lengths, "no right-column English lines found"
    assert max(lengths) <= S.RIGHT_COL_CHARS + 1
    assert sorted(lengths)[len(lengths) // 2] >= S.RIGHT_COL_CHARS - 8


def test_redaction_box_is_stamped(built):
    _, _, _, pages = built
    stamped = [t for t in pages[3:] if "25X1" in t]
    assert stamped, "redaction marker should produce a 25X1 stamp"


def test_annex_pages_numbered_with_prefix(built):
    _, labels, _, pages = built
    assert labels["annex:last"].startswith("A")
    assert any(_body_label(t) == "A1" for t in pages)


def test_map_plate_inserted_after_article_end_page(built):
    _, labels, doc, pages = built
    end_label = labels["article_end:0"]
    idx = next(i for i, t in enumerate(pages) if _body_label(t) == end_label)
    plate = doc[idx + 1]
    assert plate.get_images()
    assert BANNER not in pages[idx + 1]


def test_no_cjk_line_starts_with_closing_punctuation(built):
    _, _, _, pages = built
    for text in pages:
        for line in text.splitlines():
            assert not line.startswith(("。", "，", "；", "：", "）", "、"))


@pytest.mark.parametrize("day", ["18", "19", "20", "21"])
def test_sample_brief_has_no_line_starting_with_cjk_punctuation(tmp_path, sample_path, day):
    from content_schema import load_brief  # noqa: PLC0415
    out = tmp_path / "sample.pdf"
    build_pdf(load_brief(sample_path.with_name(f"2026-04-{day}.json")), out)
    for page in fitz.open(out):
        for line in page.get_text().splitlines():
            assert not line.startswith(("，", "；", "：", "？", "！", "。", "、", "）")), line


def test_hyphenated_compound_never_doubles_its_hyphen():
    from reportlab.platypus import Paragraph  # noqa: PLC0415
    import pdf_builder  # noqa: PLC0415
    from textfmt import typewriter  # noqa: PLC0415
    S.register_fonts()
    style = pdf_builder._styles()["toc"]
    text = ("<u>Taiwan Strait</u>:&nbsp; " + typewriter(
        "An early-April PLA exercise articulated a three-phase Taiwan "
        "contingency; Taipei responded with LNG-protection drills."))
    para = Paragraph(text, style)
    para.wrap(S.BLOCK_W, 1000)
    lines = ["".join(f.text for f in line.words) for line in para.blPara.lines]
    assert not any(line.startswith("-") for line in lines[1:]), lines


def test_compound_parts_are_hyphenated_separately():
    import pdf_builder  # noqa: PLC0415
    hyphenate = pdf_builder._hyphenation()["hyphenationLang"]
    heads = [head for head, _ in hyphenate("kill-chain")]
    assert "kil" not in heads
    assert all(not h.endswith("-") for h in heads)
    heads = [head for head, _ in hyphenate("air-defense")]
    assert "air-de" in heads


def test_bundled_fonts_embedded(built):
    _, _, doc, _ = built
    names = {f[3] for page in doc for f in page.get_fonts()}
    joined = " ".join(names)
    assert "IBMPlexMono" in joined
    assert "CourierPrime" in joined
    assert "EBGaramond" in joined


def test_back_cover_is_last_page(built):
    _, _, _, pages = built
    assert "Top Secret" in pages[-1]
    assert BANNER not in pages[-1]
