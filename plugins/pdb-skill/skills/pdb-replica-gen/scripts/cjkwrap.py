"""Chinese line breaking with kinsoku rules.

No closing mark (，。”...) may open a line and no opening mark (（“...)
may end one. reportlab's own splitter hangs at most one closing mark in
the margin, so a pair such as "”，" still leaves the comma at the head
of the next line; this breaker instead moves characters down until both
rules hold. Same signature and return shape as
reportlab.lib.textsplit.dumbSplit: [[unused_width, line_text], ...].
"""
from __future__ import annotations

from typing import Sequence

_FUZZ = 1e-6


def _latin(ch: str) -> bool:
    return ord(ch) < 0x3000 and not ch.isspace()


def _break_point(word: str, start: int, end: int,
                 cannot_start: str, cannot_end: str) -> int:
    """Adjust a greedy break so it neither cuts a Latin word nor breaks
    kinsoku; always leaves at least one character on the line."""
    if _latin(word[end]) and _latin(word[end - 1]):
        k = end - 1
        while k > start and _latin(word[k - 1]):
            k -= 1
        if k > start:
            end = k
    while end - start > 1 and (word[end] in cannot_start
                               or word[end - 1] in cannot_end):
        end -= 1
    return end


def kinsoku_split(word: str, widths: Sequence[float],
                  max_widths: float | Sequence[float],
                  cannot_start: str, cannot_end: str) -> list[list]:
    limits = (list(max_widths) if isinstance(max_widths, (list, tuple))
              else [max_widths])
    lines: list[list] = []
    start, n = 0, len(word)
    while start < n:
        limit = limits[min(len(lines), len(limits) - 1)]
        end, used = start, 0.0
        while end < n and used + widths[end] <= limit + _FUZZ:
            used += widths[end]
            end += 1
        end = max(end, start + 1)
        if end < n:
            end = _break_point(word, start, end, cannot_start, cannot_end)
        lines.append([limit - sum(widths[start:end]), word[start:end].strip()])
        start = end
    return lines
