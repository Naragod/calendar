# Working on the calendar

`README.md` shows how to run the tool. This file shows how to change it safely, and what Mateo wants.

## Where things stand (17 November 2026)

- The 2027 and 2028 posters in `output/` are ready to print at 60 × 40 in.
- Every digit and letter comes from the font Inter.
- 218 tests pass.
- The code lives at https://github.com/Naragod/calendar.

## Commands

Run each one from the repo folder.

| Goal | Command |
|---|---|
| Make the print files | `.venv/bin/yearly_calendar 2027 2028` |
| Take a quick look | `.venv/bin/yearly_calendar 2027 --preview` |
| Run the tests | `.venv/bin/python -m pytest -q` |
| Lint | `.venv/bin/python -m pyflakes src tools tests` |
| Install the dev tools | `.venv/bin/pip install -e '.[dev]'` |

The tool draws with Homebrew's `cairo`. If the venv breaks, follow the setup steps in `README.md`.

## How the code fits together

Settings → a scene of plain data → SVG → PNG and PDF. Nothing draws until `svg.py`.

1. `config.py` loads `calendar.toml`, then presets, then `--set` values. It checks them all.
2. `scene.py` builds the grid. `model.py` adds the day boxes. `legend.py` adds the white tiles.
3. `svg.py` draws the scene. `export.py` turns the SVG into a PNG and a PDF.

## How to check a change

**Same poster:** render SVGs to a scratch folder. They must match `output/` byte for byte.

```sh
.venv/bin/yearly_calendar 2027 2028 --formats svg --out /tmp/check
cmp output/2027/2027_Yearly_Calendar.svg /tmp/check/2027_Yearly_Calendar.svg
```

**New look:** render a 100 dpi PNG with `--out`. Find each changed box in `build_scene(...).cells`, and multiply its points by dpi / 72 × `scene.scale`. The scale is 1 unless `--size` or `page.fit` is on. Crop it with PIL from the venv. Look at the crop before you show Mateo.

**Then:**

1. Run the tests and pyflakes.
2. Render 2027 and 2028 into `output/`.
3. If the look changed, render a 27 dpi PNG of 2027 to `docs/preview.png`.
4. Tell Mateo what changed on the poster.

## Things to watch for

- **Glyphs.** `assets/digits.json` holds Inter's digits at weights 400 and 700. `tools/extract_digits.py` rebuilds it.
- **Letters.** `assets/letters.json` holds Inter's letters. A missing letter stops the render. Add it with `tools/extract_letters.py`.
- **Long holiday names.** A box fits about 170 pt of label text. A longer name wraps and crowds the day number. Shorten it in `holidays.names`.
- **Room for the white tiles.** Each tile takes at least 2 empty boxes at the start of row 0. The `"even"` staircase leaves room. The render says when a staircase leaves too few.
- **Contrast.** Black text reaches 4.5:1 on every box. Red and navy names reach 3:1. Tests check both, for 2026 to 2030.
- **Local folders.** `.gitignore` keeps `source/`, `drafts/` and `output/` on this machine. The Canva files in `source/` stay off GitHub.
- **Research.** The full design research sits in `drafts/research/`. `docs/design.md` sums it up.

## What Mateo wants

Every choice serves the 60 × 40 in print, seen on a wall from 0.5 to 2 m away.

Keep:

- bold weekend numbers
- red-letter holidays: a red number, with the name centred at the bottom
- white tiles inside the grid
- the title at its first size

Leave out:

- weekday letters under the columns
- tinted weekend boxes
- coloured bars on holidays
- legend panels with borders

Files:

- You can overwrite the files in `output/`.
- Old versions go to `drafts/`.

Writing:

- All writing follows `docs/writing_rules.md`. That means the README, help text, error messages, chat replies and commit messages.
- All writing reads at grade 5 or below.
- Keep it short.
- A commit message has 72 characters at most.
- A commit message has no `Co-Authored-By` line.

## Ideas waiting for a yes

Ask Mateo before you start any of these.

1. **Proof print.** Print 1–3 January, 25–26 December, a dark blue week and an orange week at full size. Look at them from 0.5 m and 2 m.
2. **Black ink.** The PDF is RGB, so a printer may mix black from four inks. That blurs small text. Ask the printer to use black ink alone.
3. **Mateo's own dates.** Birthdays and trips go in `[my_dates]` in `calendar.toml`. They print in navy.
4. **Month names in the grid.** Put a short "Mar" beside each month's first day. It helps people find months from across the room.
