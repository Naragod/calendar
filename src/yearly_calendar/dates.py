"""Calendar facts for one year: one record per day, with its week number."""
import calendar
import datetime as dt
from dataclasses import dataclass

WEEK_NUMBERINGS = ('blocks', 'iso')


@dataclass(frozen=True)
class Day:
    index: int          # 0-based position in the year
    date: dt.date
    week: int           # week number printed on the calendar
    week_index: int     # 0-based running count of weeks within this calendar
    is_month_start: bool
    is_month_end: bool

    @property
    def day_of_year(self):
        return self.index + 1

    @property
    def month(self):
        return self.date.month

    @property
    def day_of_month(self):
        return self.date.day


def days_in_year(year):
    return 366 if calendar.isleap(year) else 365


def week_number(date, numbering):
    """'blocks': 7-day blocks counted from 1 January. 'iso': Monday-Sunday ISO 8601 weeks."""
    if numbering == 'blocks':
        return (date.timetuple().tm_yday - 1) // 7 + 1
    if numbering == 'iso':
        return date.isocalendar()[1]
    raise ValueError(f'week numbering must be one of {WEEK_NUMBERINGS}, not {numbering!r}')


def year_days(year, numbering='blocks'):
    start = dt.date(year, 1, 1)
    days, week_index, previous = [], -1, None
    for i in range(days_in_year(year)):
        date = start + dt.timedelta(days=i)
        week = week_number(date, numbering)
        if week != previous:
            week_index, previous = week_index + 1, week
        tomorrow = date + dt.timedelta(days=1)
        days.append(Day(i, date, week, week_index, date.day == 1, tomorrow.month != date.month))
    return days
