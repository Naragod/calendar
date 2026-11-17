"""Glyph outlines (Inter digits and letters) and simple text placement.

Glyph units: cap height = 1000, baseline at y = 0, y grows downwards.
"""
import json
from dataclasses import dataclass
from pathlib import Path

ASSETS = Path(__file__).resolve().parents[2] / 'assets'
CAP = 1000.0     # cap height in glyph units


@dataclass(frozen=True)
class Glyph:
    d: str
    advance: float
    x_min: float
    x_max: float


@dataclass(frozen=True)
class Placed:
    """One glyph instance: font style, character, pen position (pt) and scale (pt per unit)."""
    style: str
    char: str
    x: float
    y: float
    scale: float


class Font:
    def __init__(self, glyphs_by_style):
        self.styles = glyphs_by_style

    @classmethod
    def load(cls):
        """Styles: 'regular' and 'bold' digits, 'text' letters. All three come from Inter."""
        styles = {}
        for name in ('digits.json', 'letters.json'):
            raw = json.loads((ASSETS / name).read_text())
            styles |= {style: {ch: Glyph(**g) for ch, g in glyphs.items()}
                       for style, glyphs in raw.items() if isinstance(glyphs, dict)}
        return cls(styles)

    def glyph(self, style, ch):
        try:
            return self.styles[style][ch]
        except KeyError:
            raise ValueError(f'the {style} font has no {ch!r}. Take it out of the text') from None

    def place(self, text, style, size, x, baseline, align):
        """Lay out `text` with its cap height = `size` pt. `x` is the ink's left edge,
        right edge or centre depending on `align`."""
        pens, ink = self._layout(text, style)
        if ink is None:
            return []
        scale = size / CAP
        left, right = ink[0] * scale, ink[1] * scale
        origin = x - {'left': left, 'right': right, 'centre': (left + right) / 2}[align]
        return [Placed(self._style(style, ch), ch, origin + p * scale, baseline, scale)
                for p, ch in zip(pens, text) if ch != ' ']

    @staticmethod
    def _style(style, ch):
        """Words ('text') borrow the 'regular' digits, so every number on the poster matches."""
        return 'regular' if style == 'text' and ch.isdigit() else style

    def width(self, text, style, size):
        """Ink width of `text` in pt at cap height `size`."""
        _, ink = self._layout(text, style)
        return 0.0 if ink is None else (ink[1] - ink[0]) * size / CAP

    def _layout(self, text, style):
        """Pen position of each character, and the (left, right) ink edges, in glyph units."""
        pens, pen = [], 0.0
        for ch in text:
            pens.append(pen)
            pen += self.glyph(self._style(style, ch), ch).advance
        inked = [(p, self.glyph(self._style(style, ch), ch)) for p, ch in zip(pens, text) if ch != ' ']
        if not inked:
            return pens, None
        return pens, (min(p + g.x_min for p, g in inked), max(p + g.x_max for p, g in inked))
