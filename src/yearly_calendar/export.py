"""Turn the SVG master into PNG / PDF bytes and write the files."""
import struct
import zlib
from pathlib import Path

import cairosvg

FORMATS = ('png', 'pdf', 'svg')
POINTS_PER_INCH = 72


def write(svg_text, directory, name, formats, dpi, width_pt, height_pt):
    out_dir = Path(directory)
    out_dir.mkdir(parents=True, exist_ok=True)
    svg_bytes, paths = svg_text.encode(), []
    for fmt in formats:
        path = out_dir / f'{name}.{fmt}'
        path.write_bytes(render(svg_bytes, fmt, dpi, width_pt, height_pt))
        paths.append(path)
    return paths


def render(svg_bytes, fmt, dpi, width_pt, height_pt):
    if fmt == 'svg':
        return svg_bytes
    if fmt == 'pdf':
        return cairosvg.svg2pdf(bytestring=svg_bytes)
    px_w, px_h = round(width_pt / POINTS_PER_INCH * dpi), round(height_pt / POINTS_PER_INCH * dpi)
    return with_dpi(cairosvg.svg2png(bytestring=svg_bytes, output_width=px_w, output_height=px_h), dpi)


def with_dpi(png, dpi):
    """Insert a pHYs chunk so viewers and print shops see the intended resolution."""
    per_metre = round(dpi / 0.0254)
    body = b'pHYs' + struct.pack('>IIB', per_metre, per_metre, 1)
    chunk = struct.pack('>I', 9) + body + struct.pack('>I', zlib.crc32(body))
    ihdr_end = 8 + 4 + 4 + 13 + 4          # signature + IHDR length, type, data, crc
    return png[:ihdr_end] + chunk + png[ihdr_end:]
