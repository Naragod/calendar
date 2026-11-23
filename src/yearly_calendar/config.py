"""Settings: load calendar.toml, layer presets and overrides on top, validate.

calendar.toml in the project root holds every setting with its default; presets and user
files only need the keys they change.
"""
import tomllib
from dataclasses import dataclass, fields, is_dataclass
from pathlib import Path

from .colors import SPACES
from .dates import WEEK_NUMBERINGS
from .export import FORMATS
from .logo import POSITIONS, read as read_logo
from .marks import check_date, region
from .model import COLOR_UNITS, DIVIDER_STYLES, HIGHLIGHT_RULES, LABELS, NAME_ALIGNS, points

ROOT = Path(__file__).resolve().parents[2]
DEFAULTS = ROOT / 'calendar.toml'
PRESETS = ROOT / 'presets'


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Page:
    width: float | str
    height: float | str
    margin: float
    background: str
    fit: bool


@dataclass(frozen=True)
class Output:
    directory: str
    name: str
    formats: list
    dpi: float


@dataclass(frozen=True)
class Grid:
    columns: int
    cell_width: float
    cell_height: float
    staircase: str | list


@dataclass(frozen=True)
class Lines:
    color: str
    cell_border: float
    frame: float
    month_divider: float
    month_divider_style: str


@dataclass(frozen=True)
class Colors:
    by: str
    space: str
    even_pace: bool
    stops: list
    palette: list


@dataclass(frozen=True)
class Highlight:
    days: str
    darkness: float
    hue_shift: float
    dark_colors: list
    text_color: str


@dataclass(frozen=True)
class Labels:
    week_numbering: str
    centre: str
    top_left: str
    top_right: str
    january_day_of_month: bool
    centre_size: float
    corner_size: float
    corner_top: float
    corner_left: float
    corner_right: float
    name_align: str
    color: str


@dataclass(frozen=True)
class Weekends:
    bold: bool


@dataclass(frozen=True)
class Holidays:
    country: str
    subdivision: str
    observed: bool
    names: dict
    label: str
    color: str


@dataclass(frozen=True)
class MyDates:
    color: str
    label: str
    dates: list


@dataclass(frozen=True)
class Legend:
    show: bool


@dataclass(frozen=True)
class Overview:
    show: bool


@dataclass(frozen=True)
class Key:
    show: bool


@dataclass(frozen=True)
class Title:
    text: str
    size: float
    x: float
    baseline: float
    color: str


@dataclass(frozen=True)
class Logo:
    file: str
    height: float
    gap: float
    position: str


@dataclass(frozen=True)
class Settings:
    page: Page
    output: Output
    grid: Grid
    lines: Lines
    colors: Colors
    highlight: Highlight
    labels: Labels
    weekends: Weekends
    holidays: Holidays
    my_dates: MyDates
    legend: Legend
    overview: Overview
    key: Key
    title: Title
    logo: Logo


def load(layers=(), overrides=()):
    """Defaults, then each TOML file / preset name in `layers`, then 'a.b=value' overrides."""
    data = _read(DEFAULTS)
    for layer in layers:
        data = _merge(data, _read(_resolve(layer)))
    for item in overrides:
        data = _merge(data, _override(item))
    settings = _build(Settings, data, 'settings')
    validate(settings)
    return settings


def _merge(base, extra):
    out = dict(base)
    for key, value in extra.items():
        out[key] = _merge(base[key], value) if isinstance(value, dict) and isinstance(base.get(key), dict) else value
    return out


def _resolve(layer):
    path = Path(layer)
    if path.suffix != '.toml':
        path = PRESETS / f'{layer}.toml'
    if not path.exists():
        names = ', '.join(p.stem for p in sorted(PRESETS.glob('*.toml')))
        raise ConfigError(f'found no settings file at {layer!r}. Try a preset: {names}')
    return path


def _read(path):
    with open(path, 'rb') as f:
        return tomllib.load(f)


def _override(item):
    key, sep, raw = item.partition('=')
    if not sep:
        raise ConfigError(f'--set takes section.key=value, got {item!r}')
    try:
        value = tomllib.loads(f'v = {raw}')['v']
    except tomllib.TOMLDecodeError:
        value = raw                       # bare words are taken as text
    out = value
    for part in reversed(key.strip().split('.')):
        out = {part: out}
    return out


def _build(cls, data, path):
    if not isinstance(data, dict):
        raise ConfigError(f'{path} must be a table')
    names = {f.name for f in fields(cls)}
    unknown, missing = set(data) - names, names - set(data)
    if unknown:
        raise ConfigError(f'unknown setting(s) in {path}: {", ".join(sorted(unknown))}')
    if missing:
        raise ConfigError(f'missing setting(s) in {path}: {", ".join(sorted(missing))}')
    values = {}
    for f in fields(cls):
        value = data[f.name]
        if is_dataclass(f.type):
            value = _build(f.type, value, f'{path}.{f.name}')
        elif f.type is float and isinstance(value, int) and not isinstance(value, bool):
            value = float(value)
        elif f.type in (float, int, bool, str, list, dict) and not isinstance(value, f.type):
            raise ConfigError(f'{path}.{f.name} should be a {f.type.__name__}, got {value!r}')
        values[f.name] = value
    return cls(**values)


def _check(fn, value, name):
    """Run a check from another module and report its failure as a settings error."""
    try:
        fn(value)
    except ValueError as e:
        raise ConfigError(f'{name}: {e}') from None


def _length(value):
    """True for a page length above 0: points, or inches like "36in"."""
    try:
        return points(value) > 0
    except (TypeError, ValueError):
        return False


def validate(settings):
    def choice(value, options, name):
        if value not in options:
            raise ConfigError(f'{name} must be one of {", ".join(options)}; got {value!r}')
    for name in ('width', 'height'):
        value = getattr(settings.page, name)
        if not (value == 'auto' or _length(value)):
            raise ConfigError(f'page.{name} must be a number of points, inches like "36in", or "auto"')
        if settings.page.fit and value == 'auto':
            raise ConfigError(f'page.fit fills a page of set size. Give page.{name} a size, like "36in"')
    if settings.page.margin < 0:
        raise ConfigError('page.margin takes 0 or more points')
    if settings.grid.columns < 1 or settings.grid.cell_width <= 0 or settings.grid.cell_height <= 0:
        raise ConfigError('grid.columns, grid.cell_width and grid.cell_height must be above 0')
    if not (settings.grid.staircase in ('even', 'tight') or isinstance(settings.grid.staircase, list)):
        raise ConfigError('grid.staircase must be "even", "tight" or a list of numbers, like [4, 3, 2, 1]')
    for entry in settings.my_dates.dates:
        if not isinstance(entry, dict) or 'date' not in entry or set(entry) - {'date', 'until', 'text'}:
            raise ConfigError(f'each of my_dates.dates takes a "date". It can also take "until" and "text": {entry!r}')
        for key in ('date', 'until'):
            if key in entry:
                _check(check_date, entry[key], f'my_dates.dates {key}')
    logo = settings.logo
    if logo.height <= 0 or logo.gap < 0:
        raise ConfigError('logo.height must be above 0, and logo.gap 0 or more')
    if logo.file:
        _check(read_logo, logo.file, 'logo.file')
    h = settings.holidays
    if h.country:
        _check(lambda code: region(code, h.subdivision), h.country, 'holidays')
    if settings.output.dpi <= 0:
        raise ConfigError('output.dpi must be above 0')
    for name, template in (('output.name', settings.output.name), ('title.text', settings.title.text)):
        try:
            template.format(year=2000)
        except (KeyError, IndexError, ValueError):
            raise ConfigError(f'{name} can use {{year}} and no other name in braces; got {template!r}') from None
    choice(settings.lines.month_divider_style, DIVIDER_STYLES, 'lines.month_divider_style')
    choice(settings.colors.by, COLOR_UNITS, 'colors.by')
    choice(settings.colors.space, SPACES, 'colors.space')
    choice(settings.highlight.days, HIGHLIGHT_RULES, 'highlight.days')
    choice(settings.labels.week_numbering, WEEK_NUMBERINGS, 'labels.week_numbering')
    choice(settings.labels.name_align, NAME_ALIGNS, 'labels.name_align')
    choice(settings.logo.position, POSITIONS, 'logo.position')
    for slot in ('centre', 'top_left', 'top_right'):
        choice(getattr(settings.labels, slot), LABELS, f'labels.{slot}')
    for fmt in settings.output.formats:
        choice(fmt, FORMATS, 'output.formats')
    if not settings.colors.palette and len(settings.colors.stops) < 2:
        raise ConfigError('colors.stops takes at least two stops. A colors.palette list also works')
    for stop in settings.colors.stops:
        if set(stop) != {'at', 'color'}:
            raise ConfigError(f'each colour stop takes an "at" and a "color": {stop!r}')
    if settings.highlight.dark_colors and len(settings.highlight.dark_colors) != 12:
        raise ConfigError('highlight.dark_colors takes 12 colours, one per month. An empty list [] also works')
