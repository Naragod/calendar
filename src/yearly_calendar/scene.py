"""Assemble a year's scene: grid, day cells, legend tiles, month borders, frame, title and logo."""
from dataclasses import replace

from . import colors
from .dates import year_days
from .layout import build_grid, grid_lines, offset_outline, outline
from .legend import TILE_CELLS, legend_tiles, make_legend
from .logo import by_title
from .model import Scene, day_colors, day_marks, fit_grid, make_cell, make_title, month_dividers, page_size


def build_scene(year, settings, font):
    days = year_days(year, settings.labels.week_numbering)
    g = settings.grid
    tiles = legend_tiles(settings)
    grid = build_grid(len(days), g.columns, g.cell_width, g.cell_height, g.staircase, (TILE_CELLS,) * len(tiles))
    grid, scale = fit_grid(grid, settings.page, settings.lines.frame) if settings.page.fit else (grid, 1.0)
    width, height = page_size(grid, settings.page, settings.lines.frame, scale)
    grid = replace(grid, x=(width - grid.width) / 2, y=(height - grid.height) / 2)
    slots = grid.slots()[grid.spare:]
    fills = [colors.to_hex(c) for c in day_colors(days, settings.colors)]
    marks = day_marks(year, settings)
    cells = tuple(make_cell(day, grid.cell_rect(*slot), fill, marks.get(day.date, []), settings, font)
                  for day, slot, fill in zip(days, slots, fills))
    holiday_labels = [settings.holidays.label] if settings.holidays.country else []
    legend, samples, outlines = make_legend(tiles, grid, days, fills[0], holiday_labels, settings, font)
    lines, inner = settings.lines, outline(grid)
    return Scene(
        width=width, height=height, background=settings.page.background, cells=cells, legend=legend + samples,
        line_color=lines.color, cell_border=lines.cell_border, grid_lines=tuple(grid_lines(grid)),
        month_divider=lines.month_divider,
        dividers=tuple(month_dividers(days, slots, grid, lines.month_divider_style == 'fade')),
        frame_outer=tuple(offset_outline(inner, lines.frame)), frame_inner=tuple(inner),
        patches=outlines, title=make_title(year, grid, settings.title, font),
        logo=by_title(year, grid, settings, font), scale=scale)
