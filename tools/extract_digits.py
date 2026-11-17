"""One-off: turn Inter's digits into outlines for every number on the calendar.

'regular' (wght 400) draws the day numbers. 'bold' (wght 700) draws weekend numbers and the title.
Both sets hold the digits, the comma and the space. Inter's digits stand at cap height, so
labels.centre_size and the other sizes in calendar.toml measure the digits' height.

Usage:
    .venv/bin/python tools/extract_digits.py Inter[opsz,wght].ttf assets/digits.json
"""
import sys

from extract_letters import UNITS, instance, outlines, write

CHARS = ' ,0123456789'


def main(ttf_path, out_path):
    write({'source': 'Inter (SIL Open Font License 1.1), regular wght 400, bold wght 700, opsz 14',
           'units': UNITS,
           'regular': outlines(instance(ttf_path, 400), CHARS),
           'bold': outlines(instance(ttf_path, 700), CHARS)}, out_path)
    print(f'wrote {out_path}: {len(CHARS)} glyphs in regular and bold')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
