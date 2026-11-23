"""Draw a Scene as an SVG document (the vector master for PNG and PDF export)."""
import math


def to_svg(scene, font):
    boxes = list(scene.cells) + list(scene.legend)
    highlighted = [box for box in boxes if box.highlight]
    faded = [div.segment for div in scene.dividers if div.fades]
    solid = [div.segment for div in scene.dividers if not div.fades]
    texts = [text for box in boxes for text in box.texts] + ([scene.title] if scene.title else [])
    defs = (_glyph_defs(texts, font)
            + [_highlight_gradient(f'hl{i}', box) for i, box in enumerate(highlighted)]
            + [_fade_gradient(f'fd{i}', segment, scene.line_color) for i, segment in enumerate(faded)])
    body = [
        f'<rect width="{_num(scene.width)}" height="{_num(scene.height)}" fill="{scene.background}"/>',
        *_cell_groups(boxes),
        *(_rect(box.rect, f'url(#hl{i})') for i, box in enumerate(highlighted)),
        *(_patch(patch, scene.line_color) for patch in scene.patches),
        *([_lines(solid, scene.month_divider, scene.line_color)] if solid else []),
        *(f'<path d="{_segment(segment)}" fill="none" stroke="url(#fd{i})" stroke-width="{_num(scene.month_divider)}"/>'
          for i, segment in enumerate(faded)),
        _lines(scene.grid_lines, scene.cell_border, scene.line_color),     # cell borders stay unbroken
        f'<path d="{_poly(scene.frame_outer)} {_poly(scene.frame_inner)}" fill="{scene.line_color}" fill-rule="evenodd"/>',
        *(_text(text) for text in texts),
        *([_logo(scene.logo)] if scene.logo else []),
    ]
    w, h = _num(scene.width), _num(scene.height)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{w}pt" height="{h}pt" viewBox="0 0 {w} {h}">\n'
            f'<defs>\n' + '\n'.join(defs) + '\n</defs>\n' + '\n'.join(body) + '\n</svg>\n')


def _num(v):
    """Compact number formatting for SVG coordinates."""
    s = f'{v:.3f}'.rstrip('0').rstrip('.')
    return '0' if s == '-0' else s


def _glyph_id(style, ch):
    return f'{style[0]}{ord(ch)}'


def _glyph_defs(texts, font):
    used = sorted({(g.style, g.char) for text in texts for g in text.glyphs})
    return [f'<path id="{_glyph_id(style, ch)}" d="{font.glyph(style, ch).d}"/>' for style, ch in used]


def _rect(r, fill=None):
    paint = f' fill="{fill}"' if fill else ''
    return f'<rect x="{_num(r.x)}" y="{_num(r.y)}" width="{_num(r.w)}" height="{_num(r.h)}"{paint}/>'


def _patch(patch, line_color):
    r = patch.rect
    stroke = f' stroke="{line_color}" stroke-width="{_num(patch.outline)}"' if patch.outline else ''
    return f'<rect x="{_num(r.x)}" y="{_num(r.y)}" width="{_num(r.w)}" height="{_num(r.h)}" fill="{patch.fill}"{stroke}/>'


def _cell_groups(cells):
    """One group per fill colour keeps the file small."""
    groups = {}
    for cell in cells:
        groups.setdefault(cell.fill, []).append(_rect(cell.rect))
    return [f'<g fill="{fill}">' + ''.join(rects) + '</g>' for fill, rects in groups.items()]


def _highlight_gradient(gid, cell):
    r, (light, dark) = cell.rect, cell.highlight
    return (f'<radialGradient id="{gid}" gradientUnits="userSpaceOnUse" cx="{_num(r.x)}" cy="{_num(r.y)}" '
            f'fx="{_num(r.x)}" fy="{_num(r.y)}" r="{_num(math.hypot(r.w, r.h))}">'
            f'<stop offset="0" stop-color="{light}"/><stop offset="1" stop-color="{dark}"/></radialGradient>')


def _fade_gradient(gid, s, color):
    """Transparent at the segment's far end, solid where it meets the vertical month line."""
    return (f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="{_num(s.x1)}" y1="{_num(s.y1)}" '
            f'x2="{_num(s.x2)}" y2="{_num(s.y2)}"><stop offset="0" stop-color="{color}" stop-opacity="0"/>'
            f'<stop offset="1" stop-color="{color}"/></linearGradient>')


def _segment(s):
    return f'M{_num(s.x1)} {_num(s.y1)}L{_num(s.x2)} {_num(s.y2)}'


def _lines(segments, width, color):
    d = ' '.join(_segment(s) for s in segments)
    return f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{_num(width)}" stroke-linecap="square"/>'


def _poly(pts):
    return 'M' + 'L'.join(f'{_num(x)} {_num(y)}' for x, y in pts) + 'Z'


def _text(text):
    uses = ''.join(f'<use xlink:href="#{_glyph_id(g.style, g.char)}" '
                   f'transform="translate({_num(g.x)} {_num(g.y)}) scale({_num(g.scale)})"/>' for g in text.glyphs)
    return f'<g fill="{text.color}">{uses}</g>'


def _logo(logo):
    r, box = logo.rect, ' '.join(_num(v) for v in logo.view_box)
    return (f'<svg x="{_num(r.x)}" y="{_num(r.y)}" width="{_num(r.w)}" height="{_num(r.h)}" '
            f'viewBox="{box}">{logo.inner}</svg>')
