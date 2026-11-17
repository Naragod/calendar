"""Days to mark on the calendar: public holidays (from the `holidays` package) and your own dates."""
import datetime as dt
from dataclasses import dataclass

import holidays


@dataclass(frozen=True)
class Mark:
    date: dt.date
    text: str           # empty on the later days of a multi-day entry
    kind: str           # 'holiday' or 'mine'


def region(country, subdivision, observed=False, year=None):
    """The `holidays` package's calendar for a country (ISO code, e.g. "CA") and optional
    subdivision (e.g. "ON"). Raises ValueError for an unknown country or subdivision."""
    try:
        return holidays.country_holidays(country, subdiv=subdivision or None, years=year, observed=observed)
    except NotImplementedError as e:
        raise ValueError(str(e)) from None


def public_holidays(country, subdivision, observed, year):
    """The region's public holidays in `year`, with typographic apostrophes; none without a country."""
    if not country:
        return []
    found = region(country, subdivision, observed, year)
    return [Mark(date, name.replace("'", '’'), 'holiday') for date, name in sorted(found.items())]


def my_dates(entries, year):
    """Your dates: 'MM-DD' repeats every year, 'YYYY-MM-DD' is one year only. 'until' makes a
    range, which may cross New Year. The text goes on the range's first day in this year."""
    marks = []
    for entry in entries:
        repeats = len(entry['date'].split('-')) == 2
        for base in ((year - 1, year) if repeats else (None,)):
            start = _parse(entry['date'], base)
            if start is None:
                continue
            end = _parse(entry.get('until', entry['date']), start.year) or start
            if end < start:
                end = end.replace(year=end.year + 1)
            days = [start + dt.timedelta(days=i) for i in range((end - start).days + 1)]
            days = [day for day in days if day.year == year]
            marks += [Mark(day, entry.get('text', '') if i == 0 else '', 'mine') for i, day in enumerate(days)]
    return marks


def check_date(text):
    """Raise ValueError unless `text` is 'MM-DD' or 'YYYY-MM-DD'."""
    if not isinstance(text, str) or len(text.split('-')) not in (2, 3):
        raise ValueError(f'{text!r} is not a date. Write "MM-DD" or "YYYY-MM-DD"')
    _parse(text, 2000)                      # a leap year, so 02-29 passes


def _parse(text, year):
    """'MM-DD' in `year`, or 'YYYY-MM-DD'. None for 29 February in a common year."""
    parts = [int(p) for p in text.split('-')]
    entry_year, (month, day) = (parts[0], parts[1:]) if len(parts) == 3 else (year, parts)
    try:
        return dt.date(entry_year, month, day)
    except ValueError:
        if (month, day) == (2, 29):
            return None
        raise ValueError(f'{text!r} is not a real date') from None
