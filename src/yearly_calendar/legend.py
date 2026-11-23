"""Legend tiles at the start of the first row, drawn like day cells but white."""
import math
from typing import NamedTuple

from .layout import Rect
from .model import LABELS, Cell, Patch, Text, dark_corner, place_labels, slot_labels

KEY_HIGHLIGHT = {'month_end': 'month end', 'month_start': 'month start', 'none': ''}
WEEK_NOTES = {'blocks': 'Week 1 is 1–7 January', 'iso': 'Weeks run Monday to Sunday'}
MONTHS = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')
TILE_CELLS = 2                     # minimum width, in cells, of each legend tile


class TileContext(NamedTuple):
    grid: object
    days: list
    fill: str                      # the first week's colour, for the month-end sample
    holiday_labels: list           # the key's holiday line, e.g. "Ontario public holiday"; empty without holidays
    settings: object
    font: object


def legend_tiles(settings):
    """Legend tiles in reading order: the month table, the cell anatomy, then the key beside 1 January."""
    return [kind for kind, on in (('overview', settings.overview.show), ('anatomy', settings.legend.show),
                                  ('key', settings.key.show)) if on]


def make_legend(tiles, grid, days, fill, holiday_labels, settings, font):
    """Legend tiles drawn like day cells (same borders, type sizes and label positions) but
    white, so they never read as days. The key's month-end sample keeps the first week's colour."""
    builders = {'overview': overview_tile, 'anatomy': anatomy_tile, 'key': key_tile}
    ctx = TileContext(grid, days, fill, holiday_labels, settings, font)
    cells, samples, outlines = [], [], []
    for kind, rect in zip(tiles, grid.tile_rects()):
        texts, sample_cells, sample_outlines = builders[kind](rect, ctx)
        cells.append(Cell(None, rect, settings.page.background, None, texts))      # white: not a day
        samples += sample_cells
        outlines += sample_outlines
    return tuple(cells), tuple(samples), tuple(outlines)


def tile_rows(rect, cfg, n):
    """Baselines of n text rows spread from a cell's top-label row to its bottom-label row."""
    first, last = rect.y + cfg.corner_top + cfg.corner_size, rect.y + rect.h - cfg.corner_top
    return [first + (last - first) * i / max(1, n - 1) for i in range(n)]


def anatomy_tile(rect, ctx):
    """Words in the positions of the labels they explain, including where holiday names go."""
    days, settings, font = ctx.days, ctx.settings, ctx.font
    cfg = settings.labels
    kinds = (cfg.centre, cfg.top_left, cfg.top_right)
    words = [legend_words(kind, cfg, len(days)) for kind in kinds]
    room = rect.w - cfg.corner_left - cfg.corner_right - cfg.corner_size
    if font.width(words[1], 'text', cfg.corner_size) + font.width(words[2], 'text', cfg.corner_size) > room:
        words[1:] = [LABELS[kind][1] for kind in kinds[1:]]          # narrow tile: drop the notes
    texts = place_labels(slot_labels(rect, cfg, words, cfg.corner_size), 'text', rect, None, settings, font)
    if ctx.holiday_labels:
        x = rect.x + rect.w / 2 if cfg.name_align == 'centre' else rect.x + cfg.corner_left      # as in mark_names
        texts += (Text(tuple(font.place('holiday name', 'text', cfg.corner_size, x,
                                        rect.y + rect.h - cfg.corner_top, cfg.name_align)), settings.holidays.color),)
    return texts, (), ()


def legend_words(kind, cfg, n_days):
    """Legend wording for a label kind, with a short note where the number needs one."""
    words = LABELS[kind][1]
    if kind == 'day_of_year':
        return f'{words} (1–{n_days})'
    if kind == 'day_of_month' and not cfg.january_day_of_month:
        return f'{words} (from February)'
    return words


def overview_tile(rect, ctx):
    """'Day of year on the 1st': a heading in the top-left slot, then each month's name with the
    day-of-year number of its first day, in as many columns (up to 4) as fit with clear gaps.
    Names align left and numbers align right within each column."""
    days, settings, font = ctx.days, ctx.settings, ctx.font
    cfg = settings.labels
    size, gap = cfg.corner_size, cfg.corner_size * 0.5
    starts = [day for day in days if day.is_month_start]
    entries = [(MONTHS[d.month - 1], str(d.day_of_year)) for d in starts]
    entry_w = max(font.width(name, 'text', size) + gap + font.width(number, 'regular', size) for name, number in entries)
    inner = rect.w - cfg.corner_left - cfg.corner_right
    columns = next(n for n in (4, 3, 2) if (inner - entry_w) / (n - 1) >= entry_w + size or n == 2)
    step = (inner - entry_w) / (columns - 1)
    rows = tile_rows(rect, cfg, 1 + math.ceil(len(entries) / columns))
    texts = [Text(tuple(font.place('Day of year on the 1st', 'text', size, rect.x + cfg.corner_left, rows[0], 'left')),
                  cfg.color)]
    for i, (name, number) in enumerate(entries):
        x, y = rect.x + cfg.corner_left + (i % columns) * step, rows[1 + i // columns]
        texts.append(Text(tuple(font.place(name, 'text', size, x, y, 'left')), cfg.color))
        texts.append(Text(tuple(font.place(number, 'regular', size, x + entry_w, y, 'right')), cfg.color))
    return tuple(texts), (), ()


def key_tile(rect, ctx):
    """One row per marking, each led by a real sample of it: bold weekend numbers, the holiday
    red, a small month-end cell; then how weeks are counted."""
    grid, days, fill, settings, font = ctx.grid, ctx.days, ctx.fill, ctx.settings, ctx.font
    cfg = settings.labels
    size, gap = cfg.corner_size, cfg.corner_size * 0.6
    rows = []
    if settings.weekends.bold:
        weekend = ' '.join(str(next(d.day_of_year for d in days if d.date.weekday() == wd)) for wd in (5, 6))
        rows.append([(weekend, 'bold', cfg.color), ('Saturday, Sunday', 'text', cfg.color)])
    marks = [(label, 'text', settings.holidays.color) for label in ctx.holiday_labels]
    if settings.my_dates.dates:
        marks.append((settings.my_dates.label, 'text', settings.my_dates.color))
    if marks:
        rows.append(marks)
    if KEY_HIGHLIGHT[settings.highlight.days]:
        rows.append([(None, None, None), (KEY_HIGHLIGHT[settings.highlight.days], 'text', cfg.color)])
    if {'week', 'week_month'} & {cfg.centre, cfg.top_left, cfg.top_right}:
        rows.append([(WEEK_NOTES[cfg.week_numbering], 'text', cfg.color)])
    sample_w = size * 2.4
    sample_h = sample_w * grid.cell_h / grid.cell_w
    texts, samples, outlines = [], [], []
    for baseline, runs in zip(tile_rows(rect, cfg, len(rows)), rows):
        x = rect.x + cfg.corner_left
        for text, style, color in runs:
            if text is None:
                box = Rect(x, baseline - size / 2 - sample_h / 2, sample_w, sample_h)
                samples.append(Cell(None, box, fill, (fill, dark_corner(fill, 1, settings.highlight)), ()))
                outlines.append(Patch(box, 'none', settings.lines.cell_border * sample_w / grid.cell_w))
                x += sample_w + gap
                continue
            texts.append(Text(tuple(font.place(text, style, size, x, baseline, 'left')), color))
            x += font.width(text, style, size) + gap
    return tuple(texts), tuple(samples), tuple(outlines)
