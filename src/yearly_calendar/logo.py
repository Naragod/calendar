"""A logo beside the title: an SVG file, scaled to a height. svg.py draws it as a nested <svg>."""
import xml.etree.ElementTree as ET
from dataclasses import dataclass, replace
from pathlib import Path

from .layout import Rect, clear_of_grid

ROOT = Path(__file__).resolve().parents[2]
SVG_NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', SVG_NS)
ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')
PLACEMENT = {'x', 'y', 'width', 'height', 'viewBox', 'preserveAspectRatio'}   # svg.py sets these
POSITIONS = ('beside', 'above')         # config.validate accepts exactly these


@dataclass(frozen=True)
class Logo:
    rect: Rect
    view_box: tuple[float, float, float, float]
    inner: str          # the file's elements in a <g> that keeps its <svg> styles, as SVG text


def read(file):
    """The file's root <svg> element and its viewBox. `file` is relative to the project folder, or absolute."""
    try:
        root = ET.parse(ROOT / Path(file).expanduser()).getroot()
    except OSError:
        raise ValueError(f'found no file at {file!r}') from None
    except ET.ParseError as e:
        raise ValueError(f'{file!r} is not an SVG file ({e})') from None
    if root.tag != f'{{{SVG_NS}}}svg':
        raise ValueError(f'{file!r} is not an SVG file')
    return root, view_box(root, file)


def view_box(root, file):
    try:
        box = tuple(float(v) for v in root.get('viewBox', '').replace(',', ' ').split())
    except ValueError:
        box = ()
    if len(box) != 4 or box[2] <= 0 or box[3] <= 0:
        raise ValueError(f'{file!r} has no viewBox. Add one, like viewBox="0 0 249 44"')
    return box


def make_logo(file, x, top, height):
    """The logo with its top-left corner at (x, top). The width keeps the picture's shape."""
    root, box = read(file)
    group = ET.Element(f'{{{SVG_NS}}}g', {k: v for k, v in root.attrib.items() if k not in PLACEMENT})
    group.extend(root)
    return Logo(Rect(x, top, height * box[2] / box[3], height), box, ET.tostring(group, encoding='unicode'))


def by_title(year, grid, settings, font):
    """"beside": the logo's top meets the top of the title digits, `gap` pt after their right edge.
    "above": the logo stands `gap` pt above the digits, centred over them."""
    cfg, title = settings.logo, settings.title
    if not cfg.file:
        return None
    text, left, digits_top = title.text.format(year=year), grid.x + title.x, grid.y + title.baseline - title.size
    width = font.width(text, 'bold', title.size)
    logo = make_logo(cfg.file, left + width + cfg.gap if text else left, digits_top, cfg.height)
    if cfg.position == 'above':
        logo = replace(logo, rect=replace(logo.rect, x=left + (width - logo.rect.w) / 2,
                                          y=digits_top - cfg.gap - cfg.height))
    if logo.rect.x < 0 or logo.rect.y < 0:
        raise ValueError(f'the logo runs off the page. Make logo.height smaller than {cfg.height:g}, '
                         'or move the title')
    if not clear_of_grid(logo.rect, grid, settings.lines.frame + settings.lines.cell_border):
        raise ValueError(f'the logo runs into the grid. Make logo.height smaller than {cfg.height:g}, or move the title')
    return logo
