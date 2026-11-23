"""Day cells as plain data: colours, labels, holiday and your-date names, month borders, title."""
import math
from dataclasses import dataclass, replace
from typing import NamedTuple

from . import colors
from .font import CAP, Placed
from .marks import my_dates, public_holidays
from .layout import Rect, Segment, month_border
from .logo import Logo

# Setting values and what they do. config.validate accepts exactly these keys.
COLOR_UNITS = {
    'day': lambda day: day.index,
    'week': lambda day: day.week_index,
    'month': lambda day: day.month - 1,
}
HIGHLIGHT_RULES = {
    'month_end': lambda day: day.is_month_end,
    'month_start': lambda day: day.is_month_start,
    'none': lambda day: False,
}
LABELS = {                       # kind: (text for a day, words for the legend)
    'day_of_year': (lambda day: str(day.day_of_year), 'day of year'),
    'day_of_month': (lambda day: str(day.day_of_month), 'day of month'),
    'week': (lambda day: str(day.week), 'week'),
    'month': (lambda day: str(day.month), 'month'),
    'week_month': (lambda day: f'{day.week}, {day.month}', 'week, month'),
    'none': (lambda day: '', ''),
}
DIVIDER_STYLES = ('fade', 'solid')
NAME_ALIGNS = ('left', 'centre')


@dataclass(frozen=True)
class Text:
    glyphs: tuple[Placed, ...]
    color: str


@dataclass(frozen=True)
class Patch:
    rect: Rect
    fill: str
    outline: float = 0                    # border width in the line colour; 0 = none


@dataclass(frozen=True)
class Cell:
    day_of_year: int | None              # None for legend tiles and samples
    rect: Rect
    fill: str
    highlight: tuple[str, str] | None     # (colour at top-left corner, colour at far corner)
    texts: tuple[Text, ...]


@dataclass(frozen=True)
class Divider:
    segment: Segment
    fades: bool                           # transparent at the segment's start, solid at its end


@dataclass(frozen=True)
class Scene:
    width: float
    height: float
    background: str
    cells: tuple[Cell, ...]
    legend: tuple[Cell, ...]            # legend tiles, then the key's month-end sample
    line_color: str
    cell_border: float
    grid_lines: tuple[Segment, ...]
    month_divider: float
    dividers: tuple[Divider, ...]
    frame_outer: tuple[tuple[float, float], ...]
    frame_inner: tuple[tuple[float, float], ...]
    patches: tuple[Patch, ...]           # the key sample's outline
    title: Text | None
    logo: Logo | None = None
    scale: float = 1.0                  # printed size / drawing size; see model.fit_grid


class Label(NamedTuple):
    text: str
    size: float         # cap height, pt
    x: float            # ink anchor: left edge, right edge or centre, per `align`
    baseline: float
    align: str


def points(length):
    """A page length in points: a number of points, or inches like "36in". ValueError otherwise."""
    if isinstance(length, str) and not length.endswith('in'):
        raise ValueError(f'{length!r} is not a length')
    return float(length[:-2]) * 72 if isinstance(length, str) else float(length)


def fit_grid(grid, page, frame):
    """Stretch the boxes to the page's shape, and the scale that takes the drawing to the page.
    The text and lines keep their size next to the boxes; the whole drawing shrinks or grows."""
    edge = 2 * (page.margin + frame)
    width, height = points(page.width), points(page.height)
    scale = min(width / (grid.width + edge), height / (grid.height + edge))
    return replace(grid, cell_w=(width / scale - edge) / grid.columns,
                   cell_h=(height / scale - edge) / grid.rows), scale


def page_size(grid, page, frame, scale=1.0):
    """The page in drawing points: the printed size divided by the scale."""
    block_w, block_h = grid.width + 2 * frame, grid.height + 2 * frame
    width = block_w + 2 * page.margin if page.width == 'auto' else points(page.width) / scale
    height = block_h + 2 * page.margin if page.height == 'auto' else points(page.height) / scale
    if block_w > width + 1e-6 or block_h > height + 1e-6:        # 1e-6: rounding left by fit_grid
        raise ValueError(f'the calendar ({block_w:.0f} x {block_h:.0f} pt) is larger than the page '
                         f'({width:.0f} x {height:.0f} pt). Make the cells smaller, or set the page size to "auto"')
    return width, height


def day_colors(days, cfg):
    """Fill colour per day. Days in the same unit (day / week / month) share one colour."""
    units = [COLOR_UNITS[cfg.by](day) for day in days]
    if cfg.palette:
        needed = max(units) + 1
        if len(cfg.palette) < needed:
            raise ValueError(f'colors.palette lists {len(cfg.palette)} colours. This year has {needed} {cfg.by}s, '
                             f'so add {needed - len(cfg.palette)} more')
        palette = [colors.parse(h) for h in cfg.palette]
        return [palette[unit] for unit in units]
    stops = [colors.parse(stop['color']) for stop in cfg.stops]
    positions = colors.even_positions(stops) if cfg.even_pace else [stop_position(stop['at'], days) for stop in cfg.stops]
    if any(b < a for a, b in zip(positions, positions[1:])):
        raise ValueError('colour stops must be in date order')
    last_unit = max(1, max(units))
    return [colors.gradient(stops, positions, unit / last_unit, cfg.space) for unit in units]


def stop_position(at, days):
    """'MM-DD' -> fraction of the year (0 = 1 Jan, 1 = 31 Dec); numbers are used as-is."""
    if isinstance(at, (int, float)):
        return float(at)
    month, day_of_month = (int(v) for v in at.split('-'))
    index = next((d.index for d in days if (d.month, d.day_of_month) == (month, day_of_month)), None)
    if index is None:
        raise ValueError(f'colour stop at {at!r} is not a date in {days[0].date.year}')
    return index / (len(days) - 1)


def make_cell(day, rect, fill, marks, settings, font):
    """A day cell. Weekends set their numbers in bold; a public holiday turns the day-of-year
    number red (a red-letter day) and names itself in the bottom-left slot."""
    cfg = settings.labels
    highlight = (fill, dark_corner(fill, day.month, settings.highlight)) \
        if HIGHLIGHT_RULES[settings.highlight.days](day) else None
    style = 'bold' if settings.weekends.bold and day.date.weekday() >= 5 else 'regular'
    labels = slot_labels(rect, cfg, [label_text(kind, day, cfg) for kind in (cfg.centre, cfg.top_left, cfg.top_right)],
                         cfg.centre_size)
    texts = place_labels(labels, style, rect, highlight, settings, font)
    is_holiday = any(mark.kind == 'holiday' for mark in marks)
    if is_holiday and not highlight and labels and labels[0].align == 'centre':
        texts = (replace(texts[0], color=settings.holidays.color),) + texts[1:]
    return Cell(day.day_of_year, rect, fill, highlight, texts + mark_names(marks, rect, highlight, settings, font))


def day_marks(year, settings):
    """{date: [Mark]}: public holidays first, then your own dates."""
    h = settings.holidays
    holidays = [replace(mark, text=h.names.get(mark.text, mark.text))
                for mark in public_holidays(h.country, h.subdivision, h.observed, year)]
    by_day = {}
    for mark in holidays + my_dates(settings.my_dates.dates, year):
        by_day.setdefault(mark.date, []).append(mark)
    return by_day


def mark_names(marks, rect, highlight, settings, font):
    """Holiday and your-date names at the bottom of the box, at the label size: on the left, or
    centred. A second name stacks above the first."""
    cfg = settings.labels
    kind_color = {'holiday': settings.holidays.color, 'mine': settings.my_dates.color}
    width = rect.w - cfg.corner_left - cfg.corner_right
    x = rect.x + rect.w / 2 if cfg.name_align == 'centre' else rect.x + cfg.corner_left
    lines = [(line, kind_color[mark.kind]) for mark in marks if mark.text
             for line in wrap(mark.text, font, cfg.corner_size, width)][:2]
    baseline = rect.y + rect.h - cfg.corner_top
    names = []
    for i, (line, color) in enumerate(reversed(lines)):
        glyphs = tuple(font.place(line, 'text', cfg.corner_size, x, baseline - i * cfg.corner_size * 1.6,
                                  cfg.name_align))
        if highlight:
            color = highlight_text_color(highlight, rect, [glyphs], font, 'auto', color)
        names.insert(0, Text(glyphs, color))
    return tuple(names)


def wrap(text, font, size, width):
    """Greedy word wrap of `text` into lines no wider than `width` pt."""
    lines, line = [], ''
    for word in text.split():
        candidate = f'{line} {word}'.strip()
        if line and font.width(candidate, 'text', size) > width:
            lines.append(line)
            candidate = word
        line = candidate
    return lines + [line] if line else lines


def dark_corner(fill, month, cfg):
    """Far-corner colour of a highlighted cell."""
    if cfg.dark_colors:
        return cfg.dark_colors[month - 1]
    return colors.to_hex(colors.darken(colors.parse(fill), cfg.darkness, cfg.hue_shift))


def label_text(kind, day, cfg):
    if kind == 'day_of_month' and day.month == 1 and not cfg.january_day_of_month:
        return ''
    return LABELS[kind][0](day)


def slot_labels(rect, cfg, texts, centre_size):
    """Non-empty labels for the (centre, top-left, top-right) texts of a cell-shaped box."""
    centre, top_left, top_right = texts
    corner_baseline = rect.y + cfg.corner_top + cfg.corner_size
    labels = [
        Label(centre, centre_size, rect.x + rect.w / 2, rect.y + (rect.h + centre_size) / 2, 'centre'),
        Label(top_left, cfg.corner_size, rect.x + cfg.corner_left, corner_baseline, 'left'),
        Label(top_right, cfg.corner_size, rect.x + rect.w - cfg.corner_right, corner_baseline, 'right'),
    ]
    return [label for label in labels if label.text]


def place_labels(labels, style, rect, highlight, settings, font):
    placed = [tuple(font.place(label.text, style, label.size, label.x, label.baseline, label.align))
              for label in labels]
    color = settings.labels.color
    if highlight:
        color = highlight_text_color(highlight, rect, placed, font, settings.highlight.text_color, color)
    return tuple(Text(glyphs, color) for glyphs in placed)


def highlight_text_color(highlight, rect, placed, font, text_color, label_color):
    """Text colour on a highlighted cell. 'labels' follows labels.color; 'auto' picks whichever of
    labels.color and white keeps the most contrast against the gradient under the glyphs' ink."""
    if text_color == 'labels':
        return label_color
    if text_color != 'auto':
        return text_color
    diagonal = math.hypot(rect.w, rect.h)
    reach = []                       # 0 at the light top-left corner, 1 at the dark far corner
    for glyphs in placed:
        for g in glyphs:
            glyph = font.glyph(g.style, g.char)
            for x in (g.x + glyph.x_min * g.scale, g.x + glyph.x_max * g.scale):
                for y in (g.y - CAP * g.scale, g.y):
                    reach.append(min(1.0, math.hypot(x - rect.x, y - rect.y) / diagonal))
    if not reach:
        return label_color
    light, dark = colors.parse(highlight[0]), colors.parse(highlight[1])
    backgrounds = [colors.mix(light, dark, t, 'srgb') for t in (min(reach), max(reach))]
    return max([label_color, '#ffffff'],
               key=lambda c: min(colors.contrast(colors.parse(c), bg) for bg in backgrounds))


def month_dividers(days, slots, grid, fade):
    dividers = []
    for day, slot in zip(days, slots):
        if not day.is_month_end or day.index == len(days) - 1:
            continue
        border = month_border(grid, *slot)
        if border.vertical:
            dividers.append(Divider(border.vertical, False))
        for part in (border.below, border.above):
            if part:
                dividers.append(Divider(part, fade))
    return dividers


def make_title(year, grid, cfg, font):
    text = cfg.text.format(year=year)
    if not text:
        return None
    return Text(tuple(font.place(text, 'bold', cfg.size, grid.x + cfg.x, grid.y + cfg.baseline, 'left')), cfg.color)
