"""Grid geometry: where each cell sits, the outline of the block, and month borders.

Cells fill the grid row by row so that the last day lands in the bottom-right corner; the
unused cells form a staircase in the top-left. Cells the staircase leaves over ("spare") sit
at the start of the first row and hold the legend, split into tiles of whole cells.
"""
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    w: float
    h: float


@dataclass(frozen=True)
class Segment:
    x1: float
    y1: float
    x2: float
    y2: float


@dataclass(frozen=True)
class MonthBorder:
    """Border after a month's last cell. Horizontal parts run from their far end to the
    corner where they meet the vertical part, so a fade can darken towards the corner."""
    vertical: Segment | None
    below: Segment | None
    above: Segment | None


@dataclass(frozen=True)
class Grid:
    columns: int
    rows: int
    cell_w: float
    cell_h: float
    x: float
    y: float
    row_starts: tuple[int, ...]   # first occupied column of each row
    spare: int = 0                # legend cells at the start of the first row
    tiles: tuple[int, ...] = ()   # widths, in cells, of the legend tiles across the spare cells

    @property
    def width(self):
        return self.columns * self.cell_w

    @property
    def height(self):
        return self.rows * self.cell_h

    def col_x(self, col):
        return self.x + col * self.cell_w

    def row_y(self, row):
        return self.y + row * self.cell_h

    def cell_rect(self, row, col):
        return Rect(self.col_x(col), self.row_y(row), self.cell_w, self.cell_h)

    def slots(self):
        """(row, col) of every cell, legend cells first, in fill order."""
        return [(r, c) for r in range(self.rows) for c in range(self.row_starts[r], self.columns)]

    def tile_rects(self):
        rects, col = [], self.row_starts[0]
        for width in self.tiles:
            rects.append(Rect(self.col_x(col), self.row_y(0), width * self.cell_w, self.cell_h))
            col += width
        return rects


def tight_staircase(empty):
    """Leading empty cells per row: a k..1 descending run, minus the one step that overshoots.

    13 -> [5, 4, 3, 1] (the original 365-day design), 12 -> [5, 4, 2, 1] (leap years).
    """
    if empty == 0:
        return []
    k = 1
    while k * (k + 1) // 2 < empty:
        k += 1
    overshoot = k * (k + 1) // 2 - empty
    return [step for step in range(k, 0, -1) if step != overshoot]


def even_staircase(empty, rows, min_spare=0):
    """The largest k..1 staircase that leaves at least `min_spare` cells, plus the cells left over.

    13 -> [4, 3, 2, 1] + 3 spare; with min_spare=6: 13 -> [3, 2, 1] + 7, 12 -> [3, 2, 1] + 6.
    """
    k = 0
    while (k + 1) * (k + 2) // 2 <= empty - min_spare and k + 1 < rows:
        k += 1
    steps, spare = list(range(k, 0, -1)), empty - k * (k + 1) // 2
    if spare == 1 and not min_spare:                # a lone spare cell joins the top step
        return [steps[0] + 1, *steps[1:]] if steps else [1], 0
    return steps, spare


def staircase_steps(staircase, empty, rows, min_spare):
    """Leading empty cells per row for a staircase setting: 'tight', 'even' or an explicit list."""
    if staircase == 'even':
        return even_staircase(empty, rows, min_spare)[0]
    if staircase != 'tight':
        return [int(s) for s in staircase]
    steps = tight_staircase(empty)
    return [empty] if len(steps) >= rows else steps     # the last row must start in column 0


def build_grid(n_cells, columns, cell_w, cell_h, staircase='even', tiles=()):
    """staircase: 'even' (regular steps, spare cells hold the legend), 'tight' (the original
    uneven steps, no spare cells) or a list of empty cells per row. `tiles` lists the legend
    tiles' minimum widths in cells; leftover spare cells widen the first tile."""
    rows = math.ceil(n_cells / columns)
    empty = rows * columns - n_cells
    steps = staircase_steps(staircase, empty, rows, sum(tiles))
    while steps and steps[-1] == 0:                 # trailing zeros are implied
        steps.pop()
    spare = empty - sum(steps)
    if spare and not tiles:                         # no legend: the spare cells widen the top step
        steps, spare = [(steps[0] if steps else 0) + spare, *steps[1:]], 0
    if spare < 0 or (steps and steps[0] + spare >= columns):
        raise ValueError(f'staircase {steps} leaves {sum(steps)} empty cells. This year has {empty} empty cells')
    if spare < sum(tiles):
        raise ValueError(f'the legend takes {sum(tiles)} cells; staircase {steps} leaves {spare}. '
                         f'Use staircase = "even", or fewer steps')
    widths = (tiles[0] + spare - sum(tiles), *tiles[1:]) if tiles else ()
    if (len(steps) >= rows or any(a < b for a, b in zip(steps, steps[1:]))
            or any(not 0 < s < columns for s in steps)):
        raise ValueError(f'staircase {steps}: list steps from largest to smallest, at most {rows - 1} steps, '
                         f'each from 1 to {columns - 1}')
    return Grid(columns, rows, cell_w, cell_h, 0.0, 0.0, tuple(steps + [0] * (rows - len(steps))), spare, widths)


def outline(grid):
    """Clockwise outline (screen coordinates, y down) of the occupied cells."""
    starts, right, bottom = grid.row_starts, grid.col_x(grid.columns), grid.row_y(grid.rows)
    pts = [(grid.col_x(starts[0]), grid.row_y(0)), (right, grid.row_y(0)), (right, bottom)]
    for r in range(grid.rows - 1, -1, -1):
        pts += [(grid.col_x(starts[r]), grid.row_y(r + 1)), (grid.col_x(starts[r]), grid.row_y(r))]
    return _simplify(pts)


def _simplify(pts):
    """Drop repeated points and points in the middle of a straight run."""
    out = []
    for p in pts:
        if not out or p != out[-1]:
            out.append(p)
    if out[0] == out[-1]:
        out.pop()
    return [p for a, p, b in zip(out[-1:] + out[:-1], out, out[1:] + out[:1])
            if not (a[0] == p[0] == b[0] or a[1] == p[1] == b[1])]


def offset_outline(pts, d):
    """Grow a clockwise orthogonal polygon outward by d (mitred corners)."""
    def normal(a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        return dy / length, -dx / length
    out = []
    for i, p in enumerate(pts):
        n_in, n_out = normal(pts[i - 1], p), normal(p, pts[(i + 1) % len(pts)])
        out.append((p[0] + d * (n_in[0] + n_out[0]), p[1] + d * (n_in[1] + n_out[1])))
    return out


def grid_lines(grid):
    """Every cell edge, merged into the fewest straight segments. Each legend tile's cells merge."""
    starts, rows, right = grid.row_starts, grid.rows, grid.col_x(grid.columns)
    inside_tiles, col = set(), starts[0]
    for width in grid.tiles:
        inside_tiles |= set(range(col + 1, col + width))
        col += width
    lines = [Segment(grid.col_x(starts[min(r, rows - 1)]), grid.row_y(r), right, grid.row_y(r))
             for r in range(rows + 1)]
    for c in range(grid.columns + 1):
        first_row = next(r for r in range(rows) if starts[r] <= c)
        if c in inside_tiles:
            first_row = 1
        lines.append(Segment(grid.col_x(c), grid.row_y(first_row), grid.col_x(c), grid.row_y(rows)))
    return lines


def month_border(grid, row, col):
    """Border between the cell at (row, col) and the next cell in fill order."""
    starts, columns = grid.row_starts, grid.columns
    corner = grid.col_x(col + 1)
    y_top, y_bottom = grid.row_y(row), grid.row_y(row + 1)
    vertical = Segment(corner, y_top, corner, y_bottom) if col + 1 < columns else None
    below = None
    if row + 1 < grid.rows:
        start = max(starts[row], starts[row + 1])
        if start <= col:
            below = Segment(grid.col_x(start), y_bottom, corner, y_bottom)
    above = None
    if row > 0 and col + 1 < columns:
        start = max(col + 1, starts[row - 1])
        if start < columns:
            above = Segment(grid.col_x(columns), y_top, grid.col_x(start), y_top)
    return MonthBorder(vertical, below, above)
