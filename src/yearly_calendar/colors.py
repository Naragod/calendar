"""Colour maths: parsing, perceptual blending (OKLab / OKLCH), darkening and contrast.

Colours are (r, g, b) tuples of sRGB floats in 0..1.
"""
import math

SPACES = ('srgb', 'oklab', 'oklch')


def parse(hex_color):
    h = hex_color.lstrip('#')
    if len(h) == 3:
        h = ''.join(ch * 2 for ch in h)
    if len(h) != 6:
        raise ValueError(f'not a #rrggbb colour: {hex_color!r}')
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def to_hex(rgb):
    return '#' + ''.join(f'{round(min(1.0, max(0.0, v)) * 255):02x}' for v in rgb)


def _to_linear(v):
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def _to_srgb(v):
    return 12.92 * v if v <= 0.0031308 else 1.055 * max(v, 0.0) ** (1 / 2.4) - 0.055


def to_oklab(rgb):
    r, g, b = (_to_linear(v) for v in rgb)
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)


def from_oklab(lab):
    L, a, b = lab
    l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    linear = (4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
              -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
              -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s)
    return tuple(min(1.0, max(0.0, _to_srgb(v))) for v in linear)


def to_oklch(rgb):
    L, a, b = to_oklab(rgb)
    return L, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360


def from_oklch(lch):
    L, C, h = lch
    return from_oklab((L, C * math.cos(math.radians(h)), C * math.sin(math.radians(h))))


def mix(c1, c2, t, space):
    if space == 'srgb':
        return tuple(a + (b - a) * t for a, b in zip(c1, c2))
    if space == 'oklab':
        return from_oklab(tuple(a + (b - a) * t for a, b in zip(to_oklab(c1), to_oklab(c2))))
    if space == 'oklch':
        (L1, C1, h1), (L2, C2, h2) = to_oklch(c1), to_oklch(c2)
        if C1 < 1e-4:
            h1 = h2
        if C2 < 1e-4:
            h2 = h1
        dh = (h2 - h1 + 180) % 360 - 180          # shorter way round the colour wheel
        return from_oklch((L1 + (L2 - L1) * t, C1 + (C2 - C1) * t, h1 + dh * t))
    raise ValueError(f'colour space must be one of {SPACES}, not {space!r}')


def even_positions(stops):
    """Stop positions spaced by perceptual distance, so the gradient changes at a steady pace."""
    labs = [to_oklab(c) for c in stops]
    steps = [math.dist(a, b) for a, b in zip(labs, labs[1:])]
    total = sum(steps) or 1.0
    out, run = [0.0], 0.0
    for step in steps:
        run += step
        out.append(run / total)
    return out


def gradient(stops, positions, t, space):
    """Colour at t (0..1) along a multi-stop gradient."""
    if t <= positions[0]:
        return stops[0]
    for i in range(1, len(stops)):
        p0, p1 = positions[i - 1], positions[i]
        if t <= p1:
            return mix(stops[i - 1], stops[i], 0.0 if p1 == p0 else (t - p0) / (p1 - p0), space)
    return stops[-1]


def darken(rgb, amount, hue_shift):
    """Lower perceptual lightness by `amount` (0 = unchanged, 1 = black) and turn the hue
    by `hue_shift` degrees."""
    L, C, h = to_oklch(rgb)
    return from_oklch((L * (1 - amount), C * (1 - 0.4 * amount), h + hue_shift))


def luminance(rgb):
    r, g, b = (_to_linear(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(c1, c2):
    """WCAG contrast ratio (1..21)."""
    hi, lo = sorted((luminance(c1), luminance(c2)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)
