import datetime as dt
import math
from io import BytesIO

import pytest
from PIL import Image

from yearly_calendar import colors, config
from yearly_calendar.cli import output_folder, overrides_from, parse_args, variant_name
from yearly_calendar.dates import days_in_year, year_days
from yearly_calendar.export import render
from yearly_calendar.font import CAP, Font
from yearly_calendar.marks import my_dates, public_holidays
from yearly_calendar.layout import Grid, Rect, build_grid, clear_of_grid, even_staircase, grid_lines, month_border, offset_outline, outline, tight_staircase
from yearly_calendar.model import day_colors
from yearly_calendar.scene import build_scene
from yearly_calendar.svg import to_svg


@pytest.fixture(scope='module')
def settings():
    return config.load()


@pytest.fixture(scope='module')
def font():
    return Font.load()


def strings(texts):
    """Rebuild each text's characters from its placed glyphs (spaces carry no glyph)."""
    return [''.join(g.char for g in t.glyphs) for t in texts]


# --- dates ---------------------------------------------------------------------------

@pytest.mark.parametrize('year, n', [(2026, 365), (2027, 365), (2028, 366), (2100, 365), (2000, 366)])
def test_days_in_year(year, n):
    assert days_in_year(year) == n
    assert len(year_days(year)) == n


def test_leap_day_is_day_60():
    days = year_days(2028)
    assert days[59].date == dt.date(2028, 2, 29)
    assert [d.day_of_year for d in days if d.is_month_end][:3] == [31, 60, 91]


def test_block_weeks():
    days = year_days(2027)
    assert [days[i].week for i in (0, 6, 7, 363, 364)] == [1, 1, 2, 52, 53]


def test_iso_weeks():
    days = year_days(2027, 'iso')
    assert days[0].week == 53 and days[3].week == 1          # Fri 1 Jan 2027 is in 2026's week 53
    assert days[0].week_index == 0 and days[3].week_index == 1


# --- layout --------------------------------------------------------------------------

@pytest.mark.parametrize('empty, steps', [(13, [5, 4, 3, 1]), (12, [5, 4, 2, 1]), (10, [4, 3, 2, 1]), (0, [])])
def test_tight_staircase(empty, steps):
    assert tight_staircase(empty) == steps
    assert sum(steps) == empty


@pytest.mark.parametrize('empty, min_spare, steps, spare', [
    (13, 0, [4, 3, 2, 1], 3), (12, 0, [4, 3, 2, 1], 2), (11, 0, [5, 3, 2, 1], 0),
    (13, 6, [3, 2, 1], 7), (12, 6, [3, 2, 1], 6)])
def test_even_staircase(empty, min_spare, steps, spare):
    assert even_staircase(empty, 18, min_spare) == (steps, spare)


@pytest.mark.parametrize('n', [365, 366])
def test_grid_holds_every_day_and_ends_bottom_right(n):
    grid = build_grid(n, 21, 197.4, 152.2)
    slots = grid.slots()
    assert len(slots) - grid.spare == n
    assert slots[-1] == (grid.rows - 1, grid.columns - 1)


def test_original_staircase_is_reproduced():
    assert build_grid(365, 21, 1, 1, 'tight').row_starts[:5] == (5, 4, 3, 1, 0)


def test_no_legend_widens_the_top_step():
    grid = build_grid(365, 21, 1, 1, 'even')
    assert (grid.row_starts[:4], grid.spare) == ((7, 3, 2, 1), 0)


def test_legend_tiles_merge_their_cells():
    grid = build_grid(365, 21, 1, 1, 'even', (2, 2, 2))   # staircase 3-2-1 leaves 7 cells: tiles 3, 2, 2
    assert grid.tiles == (3, 2, 2) and grid.row_starts[:4] == (3, 2, 1, 0)
    starts = {s.x1: s.y1 for s in grid_lines(grid) if s.x1 == s.x2}
    assert [starts[c] for c in range(3, 11)] == [0, 1, 1, 0, 1, 0, 1, 0]   # tiles span 3-5, 6-7, 8-9


def test_outline_area_matches_cells():
    grid = build_grid(366, 21, 2.0, 3.0)
    pts = outline(grid)
    area = abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]))) / 2
    assert area == pytest.approx((366 + grid.spare) * 6.0)


def test_offset_outline_square():
    square = [(0, 0), (10, 0), (10, 10), (0, 10)]
    assert offset_outline(square, 1) == [(-1, -1), (11, -1), (11, 11), (-1, 11)]


def test_january_border_matches_original():
    # 31 Jan 2026 sits in row 1, column 18 of the original design.
    grid = build_grid(365, 21, 1.0, 1.0, 'tight')
    assert grid.slots()[30] == (1, 18)
    b = month_border(grid, 1, 18)
    assert (b.vertical.x1, b.vertical.y1, b.vertical.y2) == (19, 1, 2)
    assert (b.below.x1, b.below.x2, b.below.y1) == (4, 19, 2)
    assert (b.above.x1, b.above.x2, b.above.y1) == (21, 19, 1)


# --- colours -------------------------------------------------------------------------

def test_hex_round_trip():
    assert colors.to_hex(colors.parse('#96b6ff')) == '#96b6ff'


@pytest.mark.parametrize('hex_color', ['#96b6ff', '#ffd380', '#000000', '#ffffff'])
def test_oklab_round_trip(hex_color):
    rgb = colors.parse(hex_color)
    assert colors.to_hex(colors.from_oklab(colors.to_oklab(rgb))) == hex_color


@pytest.mark.parametrize('space', colors.SPACES)
def test_mix_endpoints(space):
    a, b = colors.parse('#80c0ff'), colors.parse('#99ff99')
    assert colors.to_hex(colors.mix(a, b, 0, space)) == '#80c0ff'
    assert colors.to_hex(colors.mix(a, b, 1, space)) == '#99ff99'


def test_even_positions_span_zero_to_one():
    pos = colors.even_positions([colors.parse(c) for c in ('#000000', '#808080', '#ffffff')])
    assert pos[0] == 0 and pos[-1] == 1 and pos[0] < pos[1] < pos[2]


def test_dated_stops_hit_the_original_key_weeks():
    s = config.load(overrides=['colors.even_pace=false', 'colors.space=srgb'])
    fills = [colors.to_hex(c) for c in day_colors(year_days(2026), s.colors)]
    assert fills[0] == '#96b6ff'          # week 1
    assert fills[28] == '#80c0ff'         # week 5
    assert fills[112] == '#99ff99'        # week 17
    assert fills[364] == '#9eb3ff'        # week 53


@pytest.mark.parametrize('year', range(2026, 2031))
def test_highlight_text_meets_contrast(settings, font, year):
    """Black text keeps 4.5:1 against every gradient it sits on, at each glyph's ink corners."""
    scene = build_scene(year, settings, font)
    boxes = list(scene.cells) + list(scene.legend)
    corners = [(x, y) for box in boxes for text in box.texts for g in text.glyphs
               for x in (g.x + font.glyph(g.style, g.char).x_min * g.scale, g.x + font.glyph(g.style, g.char).x_max * g.scale)
               for y in (g.y - CAP * g.scale, g.y)]
    worst = 21.0
    for box in (b for b in boxes if b.highlight):
        r, diagonal = box.rect, math.hypot(box.rect.w, box.rect.h)
        light, dark = (colors.parse(c) for c in box.highlight)
        for x, y in corners:
            if r.x <= x <= r.x + r.w and r.y <= y <= r.y + r.h:
                t = min(1.0, math.hypot(x - r.x, y - r.y) / diagonal)
                worst = min(worst, colors.contrast((0, 0, 0), colors.mix(light, dark, t, 'srgb')))
    assert worst >= 4.5


# --- settings ------------------------------------------------------------------------

def test_presets_load():
    for preset in sorted(p.stem for p in config.PRESETS.glob('*.toml')):
        config.load([preset])


def test_override_and_unknown_key():
    assert config.load(overrides=['grid.cell_width=180']).grid.cell_width == 180.0
    with pytest.raises(config.ConfigError, match='unknown'):
        config.load(overrides=['grid.cell_wdith=180'])


# --- whole scene ---------------------------------------------------------------------

def test_scene_labels_2026(settings, font):
    scene = build_scene(2026, settings, font)
    by_day = {c.day_of_year: strings(c.texts) for c in scene.cells}
    assert by_day[1] == ['1', '1,1', 'NewYear’sDay']  # no day-of-month in January; spaces have no glyph
    assert by_day[93] == ['93', '3', '14,4', 'GoodFriday']   # the original wrongly said month 3
    assert by_day[105] == ['105', '15', '15,4']
    assert by_day[365] == ['365', '31', '53,12']
    highlighted = [c.day_of_year for c in scene.cells if c.highlight]
    assert highlighted == [31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334, 365]


def test_scene_leap_year(settings, font):
    scene = build_scene(2028, settings, font)
    assert len(scene.cells) == 366
    assert [c.day_of_year for c in scene.cells if c.highlight][:2] == [31, 60]
    assert strings(scene.cells[59].texts)[1:] == ['29', '9,2']


def test_svg_renders(settings, font):
    svg = to_svg(build_scene(2027, settings, font), font)
    # background, 365 cells, 3 legend tiles, the key's month-end sample, 12 month-end gradients
    # plus the sample's, and the sample's outline
    assert svg.startswith('<svg') and svg.count('<rect') == 1 + 365 + 3 + 1 + 12 + 1 + 1
    assert svg.count('stop-opacity="0"') == 22                             # 11 borders x 2 fading parts


def test_legend_tiles(settings, font):
    scene = build_scene(2027, settings, font)
    overview, anatomy, key, sample = scene.legend
    first_day = scene.cells[0].rect
    assert key.rect.x + key.rect.w == pytest.approx(first_day.x) and overview.rect.w == 3 * settings.grid.cell_width
    assert strings(overview.texts)[:3] == ['Dayofyearonthe1st', 'Jan', '1'] and strings(overview.texts)[-2:] == ['Dec', '335']
    assert strings(anatomy.texts) == ['dayofyear(1–365)', 'dayofmonth', 'week,month', 'holidayname']
    assert anatomy.texts[-1].color == settings.holidays.color
    assert strings(key.texts) == ['23', 'Saturday,Sunday', 'Ontariopublicholiday', 'monthend', 'Week1is1–7January']
    assert sample.highlight and all(tile.fill == settings.page.background for tile in (overview, anatomy, key))


@pytest.mark.parametrize('year', [2027, 2028])
def test_overview_entries_never_touch(settings, font, year):
    """Month entries in one row keep at least a label-size gap, also in the narrower leap-year tile."""
    overview = build_scene(year, settings, font).legend[0]
    by_row = {}
    for text in overview.texts[1:]:
        g = text.glyphs
        left, right = g[0].x, g[-1].x + font.glyph(g[-1].style, g[-1].char).x_max * g[-1].scale
        by_row.setdefault(round(g[0].y), []).append((left, right))
    for spans in by_row.values():
        entries = [(spans[i][0], spans[i + 1][1]) for i in range(0, len(spans), 2)]   # name + number
        assert all(b[0] - a[1] >= settings.labels.corner_size for a, b in zip(entries, entries[1:]))


def test_page_too_small_is_reported(font):
    s = config.load(overrides=['grid.cell_height=300'])
    with pytest.raises(ValueError, match='larger than the page'):
        build_scene(2027, s, font)


# --- regressions ---------------------------------------------------------------------

@pytest.mark.parametrize('columns', range(15, 60))
@pytest.mark.parametrize('staircase', ['even', 'tight'])
def test_staircase_keeps_column_zero_in_last_row(columns, staircase):
    assert build_grid(365, columns, 1, 1, staircase).row_starts[-1] == 0


def test_stop_on_missing_date_is_reported(font):
    s = config.load(overrides=['colors.even_pace=false',
                               'colors.stops=[{at="01-01",color="#ffffff"},{at="02-29",color="#000000"}]'])
    with pytest.raises(ValueError, match='not a date in 2027'):
        build_scene(2027, s, font)


def test_auto_text_colour_on_cell_without_labels(font):
    s = config.load(overrides=['labels.centre="day_of_month"', 'labels.top_left="none"', 'labels.top_right="none"',
                               'highlight.days="month_start"', 'highlight.text_color="auto"', 'holidays.country=""'])
    assert build_scene(2027, s, font).cells[0].texts == ()


@pytest.mark.parametrize('override', ['title.text="{yr}"', 'output.formats="png"', 'grid.columns=0', 'output.dpi=0',
                                      'holidays.country="ZZ"', 'holidays.subdivision="XX"', 'holidays.names=5', 'my_dates.dates=[{date="13-40"}]',
                                      'my_dates.dates=[{date="07-12",until="tomorrow"}]', 'logo.height=0', 'logo.gap=-1', 'labels.name_align="right"', 'logo.position="below"', 'page.width="36cm"', 'page.height="0in"', 'page.width=-5', 'page.height="in"'])
def test_bad_settings_are_reported(override):
    with pytest.raises(config.ConfigError):
        config.load(overrides=[override])


def test_short_palette_is_reported(font):
    s = config.load(['original_exact'], ['colors.by=day'])
    with pytest.raises(ValueError, match='add 312 more'):
        build_scene(2027, s, font)


def test_highlight_text_follows_label_colour(font):
    s = config.load(overrides=['labels.color="#444444"'])
    cells = build_scene(2027, s, font).cells
    assert {t.color for c in cells if c.highlight for t in c.texts} == {'#444444'}


# --- holidays, your dates, weekends --------------------------------------------------

def test_ontario_2027():
    days = [m.date.strftime('%m-%d') for m in public_holidays('CA', 'ON', False, 2027)]
    assert days == ['01-01', '02-15', '03-26', '05-24', '07-01', '09-06', '10-11', '12-25', '12-26']


def test_england_2027_substitute_days():
    marks = {m.date.strftime('%m-%d'): m.text for m in public_holidays('GB', 'ENG', True, 2027)}
    assert marks['12-27'] == 'Christmas Day (observed)' and marks['12-28'] == 'Boxing Day (observed)'
    assert marks['01-01'] == 'New Year’s Day'          # typographic apostrophe


def test_holiday_names_can_be_shortened(settings, font):
    cell = next(c for c in build_scene(2027, settings, font).cells if c.day_of_year == 284)
    assert strings(cell.texts)[-1] == 'Thanksgiving'


def test_england_preset_names_fit_one_line(font):
    s = config.load(['england'])
    for year in (2027, 2028, 2032):        # 2032: Christmas on a Saturday, so two substitute days
        for cell in build_scene(year, s, font).cells:
            names = [t for t in cell.texts if t.color == s.holidays.color and t.glyphs[0].style == 'text']
            assert len(names) <= 1, cell.day_of_year


def test_no_country_means_no_holidays():
    assert public_holidays('', '', False, 2027) == []


def test_my_dates():
    marks = my_dates([{'date': '12-30', 'until': '01-02', 'text': 'Trip'}, {'date': '02-29', 'text': 'Leap'},
                      {'date': '2028-01-01', 'text': 'Next year'}], 2027)
    assert [(m.date.strftime('%m-%d'), m.text) for m in marks] == [
        ('01-01', 'Trip'), ('01-02', ''), ('12-30', 'Trip'), ('12-31', '')]


def test_weekends_are_bold(settings, font):
    cells = build_scene(2027, settings, font).cells     # 1 Jan 2027 is a Friday
    styles = [{g.style for t in cell.texts for g in t.glyphs if g.style != 'text'} for cell in cells[:4]]
    assert styles == [{'regular'}, {'bold'}, {'bold'}, {'regular'}]
    assert cells[1].fill == build_scene(2027, config.load(overrides=['weekends.bold=false']), font).cells[1].fill


def test_holidays_are_red_letter_days(font):
    s = config.load(overrides=['my_dates.dates=[{date="12-25",text="Family dinner"}]'])
    christmas = build_scene(2027, s, font).cells[358]
    assert christmas.texts[0].color == s.holidays.color                    # the day-of-year number
    names = [(''.join(g.char for g in t.glyphs), t.color) for t in christmas.texts[-2:]]
    assert names == [('ChristmasDay', s.holidays.color), ('Familydinner', s.my_dates.color)]
    assert christmas.texts[-1].glyphs[0].x == pytest.approx(christmas.rect.x + s.labels.corner_left, abs=2)


@pytest.mark.parametrize('year', range(2026, 2031))
def test_mark_names_meet_contrast(settings, font, year):
    """Names and red numbers are large text (15.7 pt cap height is about 21.6 pt type), so WCAG asks
    3:1. The holiday red also keeps 3:1 against the black lines, so it never reads as a border."""
    fills = {cell.fill for cell in build_scene(year, settings, font).cells}
    for color in (settings.holidays.color, settings.my_dates.color):
        assert min(colors.contrast(colors.parse(color), colors.parse(f)) for f in fills) >= 3
    assert colors.contrast(colors.parse(settings.holidays.color), colors.parse(settings.lines.color)) >= 3


def test_key_lists_what_is_shown(font):
    s = config.load(overrides=['my_dates.dates=[{date="07-12",text="Mum"}]'])
    key = strings(build_scene(2027, s, font).legend[2].texts)
    assert key == ['23', 'Saturday,Sunday', 'Ontariopublicholiday', 'Yourdates', 'monthend', 'Week1is1–7January']
    s = config.load(overrides=['my_dates.dates=[{date="07-12",text="Mum"}]', 'my_dates.label="Milestones"'])
    assert 'Milestones' in strings(build_scene(2027, s, font).legend[2].texts)


# --- output folders -------------------------------------------------------------------

@pytest.mark.parametrize('argv, folder', [
    (['2027'], 'output/2027'),
    (['2027', '--preview'], 'output/2027/previews'),
    (['2027', '--preset', 'by_month'], 'output/2027/variants/by_month'),
    (['2027', '--preset', 'by_month', '--config', 'mine/my_settings.toml', '--set', 'grid.columns=20'],
     'output/2027/variants/by_month+my_settings+custom'),
    (['2027', '--set', 'weekends.shade=0', '--preview'], 'output/2027/variants/custom/previews'),
    (['2027', '--preset', 'by_month', '--size', '36x24'], 'output/2027/variants/by_month+24x36'),
])
def test_output_folder(argv, folder):
    args = parse_args(argv)
    assert output_folder('output', args.years[0], variant_name(args), args.preview).as_posix() == folder


def sized(size):
    """Settings for a poster size in inches, as --size gives them."""
    return config.load(overrides=overrides_from(parse_args(['2027', '--size', size])))


@pytest.mark.parametrize('year', [2027, 2028])
@pytest.mark.parametrize('size', [None, '12x18', '36x48'])
def test_title_clears_the_frame(settings, font, year, size):
    """The title keeps at least one cell-border width (9 pt) clear of the frame."""
    settings = sized(size) if size else settings
    scene = build_scene(year, settings, font)
    frame, gap = scene.frame_outer, settings.lines.cell_border
    glyphs = scene.title.glyphs
    x0 = glyphs[0].x + font.glyph('bold', glyphs[0].char).x_min * glyphs[0].scale - gap
    x1 = glyphs[-1].x + font.glyph('bold', glyphs[-1].char).x_max * glyphs[-1].scale + gap
    y0, y1 = glyphs[0].y - settings.title.size - gap, glyphs[0].y + gap
    def inside(x, y):                     # even-odd point-in-polygon test
        return sum((ya > y) != (yb > y) and x < xa + (y - ya) * (xb - xa) / (yb - ya)
                   for (xa, ya), (xb, yb) in zip(frame, frame[1:] + frame[:1])) % 2 == 1
    edge = [(x0 + (x1 - x0) * i / 40, y) for i in range(41) for y in (y0, y1)] + \
           [(x, y0 + (y1 - y0) * i / 40) for i in range(41) for x in (x0, x1)]
    assert not any(inside(x, y) for x, y in edge)
    assert not any(x0 <= px <= x1 and y0 <= py <= y1 for px, py in frame)


# --- logo ----------------------------------------------------------------------------

def logo_file(tmp_path, attrs='', body='<rect width="249" height="44" fill="#ff0000"/>'):
    """A red logo with the Measure logo's shape, written to a temporary file."""
    path = tmp_path / 'logo.svg'
    path.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 249 44"{attrs}>{body}</svg>')
    return str(path)


def with_logo(path, *overrides):
    return config.load(overrides=[f'logo.file="{path}"', *overrides])


def test_no_logo_by_default(settings, font):
    scene = build_scene(2027, settings, font)
    assert scene.logo is None
    assert to_svg(scene, font).count('<svg') == 1


@pytest.mark.parametrize('year', [2027, 2028])
def test_logo_sits_beside_the_title(tmp_path, font, year):
    s = with_logo(logo_file(tmp_path))
    scene = build_scene(year, s, font)
    last = scene.title.glyphs[-1]
    title_right = last.x + font.glyph('bold', last.char).x_max * last.scale
    rect = scene.logo.rect
    assert rect.h == s.logo.height and rect.w == pytest.approx(s.logo.height * 249 / 44)
    assert rect.y == pytest.approx(scene.title.glyphs[0].y - s.title.size)      # top of the digits
    assert rect.x == pytest.approx(title_right + s.logo.gap)


@pytest.mark.parametrize('attrs, body', [('', '<rect width="249" height="44" fill="#ff0000"/>'),
                                         (' fill="#ff0000"', '<rect width="249" height="44"/>')])   # a fill on <svg>
def test_logo_is_drawn(tmp_path, font, attrs, body):
    scene = build_scene(2027, with_logo(logo_file(tmp_path, attrs, body)), font)
    png = Image.open(BytesIO(render(to_svg(scene, font).encode(), 'png', 72, scene.width, scene.height))).convert('RGB')
    r = scene.logo.rect
    assert png.getpixel((round(r.x + r.w / 2), round(r.y + r.h / 2))) == (255, 0, 0)
    assert png.getpixel((round(r.x + r.w + 10), round(r.y + r.h / 2))) != (255, 0, 0)


@pytest.mark.parametrize('name, text, error', [
    ('missing.svg', None, 'found no file'),
    ('logo.svg', 'not svg', 'is not an SVG file'),
    ('logo.svg', '<html/>', 'is not an SVG file'),
    ('logo.svg', '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"/>', 'has no viewBox'),
])
def test_bad_logo_file_is_reported(tmp_path, name, text, error):
    if text is not None:
        (tmp_path / 'logo.svg').write_text(text)
    with pytest.raises(config.ConfigError, match=error):
        with_logo(tmp_path / name)


def test_logo_can_stand_above_the_title(tmp_path, font):
    s = with_logo(logo_file(tmp_path), 'logo.position="above"', 'logo.height=40', 'title.baseline=270')
    scene = build_scene(2027, s, font)
    first = scene.title.glyphs[0]
    rect = scene.logo.rect
    assert rect.y + rect.h == pytest.approx(first.y - s.title.size - s.logo.gap)
    left = first.x + font.glyph('bold', first.char).x_min * first.scale
    assert rect.x + rect.w / 2 == pytest.approx(left + font.width('2027', 'bold', s.title.size) / 2)


def test_logo_off_the_page_is_reported(tmp_path, font):
    with pytest.raises(ValueError, match='runs off the page'):
        build_scene(2027, with_logo(logo_file(tmp_path), 'logo.position="above"', 'logo.height=200'), font)


def test_logo_too_tall_is_reported(tmp_path, font):
    with pytest.raises(ValueError, match='logo.height'):
        build_scene(2027, with_logo(logo_file(tmp_path), 'logo.height=40'), font)


def test_clear_of_grid():
    grid = Grid(4, 3, 100, 100, 0, 0, (3, 1, 0))     # rows start at x 300, 100 and 0
    assert clear_of_grid(Rect(0, 0, 270, 70), grid, 30)
    assert not clear_of_grid(Rect(0, 0, 271, 70), grid, 30)      # row 0's frame starts at x 270
    assert clear_of_grid(Rect(0, 0, 70, 170), grid, 30)
    assert not clear_of_grid(Rect(0, 0, 70, 171), grid, 30)      # row 2's frame starts at y 170


def test_names_can_be_centred(font):
    s = config.load(overrides=['labels.name_align="centre"', 'my_dates.dates=[{date="07-12",text="Family dinner"}]'])
    cell = next(c for c in build_scene(2027, s, font).cells if any(t.color == s.my_dates.color for t in c.texts))
    glyphs = next(t for t in cell.texts if t.color == s.my_dates.color).glyphs
    left = glyphs[0].x + font.glyph('text', glyphs[0].char).x_min * glyphs[0].scale
    right = glyphs[-1].x + font.glyph('text', glyphs[-1].char).x_max * glyphs[-1].scale
    assert (left + right) / 2 == pytest.approx(cell.rect.x + cell.rect.w / 2)


# --- poster size ---------------------------------------------------------------------

@pytest.mark.parametrize('text, sides', [('24x36', (36, 24)), ('36X24', (36, 24)), ('36x48', (48, 36))])
def test_poster_size_puts_the_long_side_across(text, sides):
    assert parse_args(['2027', '--size', text]).size == sides


@pytest.mark.parametrize('text', ['24', '24x', 'x36', '24x36x48', '0x36', 'axb'])
def test_bad_poster_size_is_reported(text):
    with pytest.raises(SystemExit):
        parse_args(['2027', '--size', text])


@pytest.mark.parametrize('year', [2027, 2028])
@pytest.mark.parametrize('size, inches', [('12x18', (18, 12)), ('36x48', (48, 36)), ('36x40', (40, 36))])
def test_poster_fills_the_page(font, year, size, inches):
    s = sized(size)
    scene = build_scene(year, s, font)
    assert (scene.width * scene.scale, scene.height * scene.scale) == pytest.approx((inches[0] * 72, inches[1] * 72))
    xs, ys = [x for x, _ in scene.frame_outer], [y for _, y in scene.frame_outer]
    assert min(xs) == pytest.approx(s.page.margin) and max(xs) == pytest.approx(scene.width - s.page.margin)
    assert min(ys) == pytest.approx(s.page.margin) and max(ys) == pytest.approx(scene.height - s.page.margin)


def test_poster_prints_at_its_size(font):
    scene = build_scene(2027, sized('24x36'), font)
    png = Image.open(BytesIO(render(to_svg(scene, font).encode(), 'png', 10, scene.width * scene.scale,
                                    scene.height * scene.scale)))
    assert png.size == (360, 240)
    assert 'width="2592pt" height="1728pt"' in to_svg(scene, font)


def test_page_size_takes_inches(font):
    scene = build_scene(2027, config.load(overrides=['page.width="60in"', 'page.height="40in"']), font)
    assert (scene.width, scene.height, scene.scale) == (4320, 2880, 1)


def test_fit_needs_a_page_size():
    with pytest.raises(config.ConfigError, match='page.fit'):
        config.load(overrides=['page.fit=true', 'page.width="auto"'])
