from datetime import datetime, timedelta

RANGES = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 7)]


def _parse_field(text, low, high):
    values = set()
    for item in text.split(","):
        base, _, step = item.partition("/")
        if step:
            if not step.isdigit() or int(step) == 0:
                raise ValueError(f"bad step: {item!r}")
            step = int(step)
        else:
            step = 1
        if base == "*":
            start, end = low, high
        elif "-" in base:
            a, _, b = base.partition("-")
            if not (a.isdigit() and b.isdigit()):
                raise ValueError(f"bad range: {item!r}")
            start, end = int(a), int(b)
        elif base.isdigit() and not item.count("/"):
            start = end = int(base)
        else:
            raise ValueError(f"bad item: {item!r}")
        if not (low <= start <= end <= high):
            raise ValueError(f"out of range: {item!r}")
        values.update(range(start, end + 1, step))
    return values


def next_cron(expr: str, after: str) -> str:
    fields = expr.split(" ")
    if len(fields) != 5:
        raise ValueError("expected five fields")
    minutes, hours, days, months, weekdays = (_parse_field(f, lo, hi) for f, (lo, hi) in zip(fields, RANGES))
    if 7 in weekdays:
        weekdays.add(0)
    either = not fields[2].startswith("*") and not fields[4].startswith("*")

    start = datetime.strptime(after, "%Y-%m-%dT%H:%M") + timedelta(minutes=1)
    limit = start.replace(year=start.year + 8) if not (start.month == 2 and start.day == 29) else start.replace(
        year=start.year + 8, day=28)
    day = start.replace(hour=0, minute=0)
    while day <= limit:
        cron_weekday = (day.weekday() + 1) % 7  # Python: Monday=0; cron: Sunday=0
        dom_ok, dow_ok = day.day in days, cron_weekday in weekdays
        if day.month in months and ((dom_ok or dow_ok) if either else (dom_ok and dow_ok)):
            for h in sorted(hours):
                for m in sorted(minutes):
                    candidate = day.replace(hour=h, minute=m)
                    if candidate >= start:
                        return candidate.strftime("%Y-%m-%dT%H:%M")
        day += timedelta(days=1)
    raise ValueError("no matching time within 8 years")
