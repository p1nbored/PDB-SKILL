"""Shared fixtures for the pdb-replica-gen test suite."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills" / "pdb-replica-gen" / "scripts"
SAMPLES = ROOT / "skills" / "pdb-replica-gen" / "assets" / "samples"
sys.path.insert(0, str(SCRIPTS))

_EN = ("Reporting from several capitals indicates that the talks are "
       "continuing, although neither side has moved on the central issue "
       "of verification. We believe both delegations expect a pause.")
_CN = "多国首都的报道显示，谈判仍在继续，但双方在核查这一核心问题上均未让步。我们判断双方代表团都预计谈判将暂停。"


def _article(region: str, paragraphs: int = 3, **extra) -> dict:
    return {
        "title_en": f"{region.upper()}: TALKS CONTINUE",
        "title_cn": f"{region}：谈判继续",
        "region": region,
        "summary_en": f"Talks in {region} continue without a breakthrough.",
        "summary_cn": f"{region}谈判继续，但未取得突破。",
        "body_en": [_EN] * paragraphs,
        "body_cn": [_CN] * paragraphs,
        "sources": ["Reuters 2026-04-17", "Xinhua 2026-04-17"],
        **extra,
    }


@pytest.fixture
def brief_dict() -> dict:
    """A brief long enough to span several body pages, with notes and annex."""
    return {
        "date": "2026-04-18",
        "articles": [
            _article("Middle East", 4),
            _article("Russia-Ukraine", 4, body_en=[_EN, "[REDACTED:3]", _EN],
                     body_cn=[_CN, "[REDACTED:3]", _CN]),
            _article("Taiwan Strait", 5),
            _article("Korea", 3),
        ],
        "notes": [
            {"region": "Poland", "text_en": _EN, "text_cn": _CN,
             "summary_en": "Poland's coalition talks have stalled.",
             "summary_cn": "波兰联合政府谈判陷入停滞。"},
            {"region": "Venezuela", "text_en": _EN, "text_cn": _CN},
        ],
        "annex": {
            "title_en": "Iran after the ceasefire",
            "title_cn": "停火之后的伊朗",
            "summary_en": "The ceasefire has bought time but not a settlement.",
            "summary_cn": "停火赢得了时间，但并未带来解决方案。",
            "body_en": [_EN] * 8,
            "body_cn": [_CN] * 8,
        },
    }


@pytest.fixture
def sample_path() -> Path:
    return SAMPLES / "2026-04-18.json"
