"""One-off: turn Inter's letters into outlines for words on the calendar (legend, month names).

Inter (SIL Open Font License 1.1) matches the weight of the calendar's digits at wght 400.
Download: https://github.com/google/fonts/raw/main/ofl/inter/Inter%5Bopsz,wght%5D.ttf

Usage:
    .venv/bin/python tools/extract_letters.py Inter[opsz,wght].ttf assets/letters.json

Output units match assets/digits.json: cap height = 1000, baseline y = 0, y grows downwards.
"""
import json
import sys

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

CHARS = [chr(c) for c in range(32, 127)] + [chr(c) for c in range(0xC0, 0x100)] + ['–', '’', '·']
UNITS = 'cap height = 1000, baseline y = 0, y grows downwards'


def instance(ttf_path, weight):
    """Inter at one weight, at the 14 pt optical size."""
    return instancer.instantiateVariableFont(TTFont(ttf_path), {'wght': weight, 'opsz': 14})


def outlines(font, chars):
    """Each character's outline, advance and ink edges, scaled to cap height = 1000."""
    scale = 1000 / font['OS/2'].sCapHeight
    glyphs, cmap, metrics = font.getGlyphSet(), font.getBestCmap(), font['hmtx'].metrics
    out = {}
    for ch in chars:
        name = cmap[ord(ch)]
        pen, bounds = SVGPathPen(glyphs, ntos=lambda v: f'{v:.1f}'.rstrip('0').rstrip('.')), BoundsPen(glyphs)
        for target in (pen, bounds):
            glyphs[name].draw(TransformPen(target, (scale, 0, 0, -scale, 0, 0)))
        x_min, _, x_max, _ = bounds.bounds or (0, 0, 0, 0)
        out[ch] = {'d': pen.getCommands(), 'advance': round(metrics[name][0] * scale, 1),
                   'x_min': round(x_min, 1), 'x_max': round(x_max, 1)}
    return out


def write(data, out_path):
    with open(out_path, 'w') as f:
        json.dump(data, f, indent=1, sort_keys=True, ensure_ascii=False)


def main(ttf_path, out_path):
    text = outlines(instance(ttf_path, 400), CHARS)
    write({'source': 'Inter (SIL Open Font License 1.1), wght 400, opsz 14', 'units': UNITS, 'text': text}, out_path)
    print(f'wrote {out_path}: {len(text)} glyphs')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
