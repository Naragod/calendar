"""Command line: yearly_calendar 2027 [2028 ...] [--preset NAME] [--config FILE] [--set KEY=VALUE]

Files go to output/YEAR/. Runs that change the look go to output/YEAR/variants/NAME/, and
--preview runs to a previews/ folder inside either, so they never replace the print files.
"""
import argparse
import sys
import time
from pathlib import Path

from . import config, export
from .font import Font
from .scene import build_scene
from .svg import to_svg

PREVIEW_DPI = 30


def parse_args(argv):
    p = argparse.ArgumentParser(prog='yearly_calendar', description='Make the yearly calendar poster.')
    p.add_argument('years', nargs='+', type=int, help='the years to make, like 2027 2028')
    p.add_argument('--preset', action='append', default=[], metavar='NAME',
                   help='use presets/NAME.toml. Repeat to stack presets')
    p.add_argument('--config', action='append', default=[], metavar='FILE',
                   help='use your own settings file. Repeat to stack files')
    p.add_argument('--set', action='append', default=[], metavar='KEY=VALUE', dest='overrides',
                   help='change one setting, like grid.cell_width=180')
    p.add_argument('--preview', action='store_true', help=f'make a quick {PREVIEW_DPI} dpi PNG in a previews/ folder')
    p.add_argument('--formats', help='the files to make, like png,pdf,svg')
    p.add_argument('--dpi', type=float, help='dots per inch in the PNG')
    p.add_argument('--out', help='save the files in this folder, in place of output/YEAR/')
    return p.parse_args(argv)


def overrides_from(args):
    """--set items, then the --preview / --formats / --dpi shortcuts as the same 'key=value' form."""
    overrides = list(args.overrides)
    formats = args.formats or ('png' if args.preview else None)
    dpi = args.dpi if args.dpi is not None else (PREVIEW_DPI if args.preview else None)
    if formats:
        overrides.append(f'output.formats={[f.strip() for f in formats.split(",")]!r}')
    if dpi is not None:
        overrides.append(f'output.dpi={dpi}')
    return overrides


def variant_name(args):
    """Folder name for a run that changes the default look: presets, settings files, then 'custom'
    for --set. Empty for the default look."""
    return '+'.join(args.preset + [Path(c).stem for c in args.config] + (['custom'] if args.overrides else []))


def output_folder(root, year, variant='', preview=False):
    folder = Path(root) / str(year)
    if variant:
        folder = folder / 'variants' / variant
    return folder / 'previews' if preview else folder


def render_year(year, settings, font, folder):
    start = time.time()
    try:
        scene = build_scene(year, settings, font)
    except ValueError as e:
        sys.exit(f'{year}: {e}')
    out = settings.output
    paths = export.write(to_svg(scene, font), folder, out.name.format(year=year),
                         out.formats, out.dpi, scene.width, scene.height)
    print(f'{year}: ' + ', '.join(str(p) for p in paths) + f'  ({time.time() - start:.1f}s)')


def main(argv=None):
    args = parse_args(argv)
    try:
        settings = config.load(args.preset + args.config, overrides_from(args))
    except ValueError as e:
        sys.exit(f'settings error: {e}')
    font = Font.load()
    root = config.ROOT / settings.output.directory
    for year in args.years:
        folder = Path(args.out).expanduser().resolve() if args.out else \
            output_folder(root, year, variant_name(args), args.preview)
        render_year(year, settings, font, folder)
