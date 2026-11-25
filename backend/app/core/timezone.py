import logging
from datetime import date, datetime, timezone
from typing import Optional, Union
from zoneinfo import ZoneInfo
from app.core.config import settings

logger = logging.getLogger(__name__)


def get_gym_tz() -> ZoneInfo:
    """Returns the ZoneInfo for the configured gym timezone."""
    tz_str = getattr(settings, "TIMEZONE", "Asia/Kolkata") or "Asia/Kolkata"
    try:
        return ZoneInfo(tz_str)
    except Exception as exc:
        logger.warning("Invalid timezone '%s', defaulting to 'Asia/Kolkata': %s", tz_str, exc)
        try:
            return ZoneInfo("Asia/Kolkata")
        except Exception:
            return ZoneInfo("UTC")


def now_utc() -> datetime:
    """Returns the current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def now_gym() -> datetime:
    """Returns the current datetime in the gym's configured timezone."""
    return datetime.now(get_gym_tz())


def today_gym() -> date:
    """Returns the current date in the gym's configured timezone."""
    return now_gym().date()


def to_gym_timezone(dt: Optional[datetime]) -> Optional[datetime]:
    """Converts a UTC or naive datetime to the gym's configured timezone."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(get_gym_tz())


def format_time(dt: Optional[datetime]) -> Optional[str]:
    """Formats a datetime as 'HH:MM AM/PM' in the gym's configured timezone."""
    if dt is None:
        return None
    gym_dt = to_gym_timezone(dt)
    return gym_dt.strftime("%I:%M %p")


def format_full_date(d: Optional[Union[date, datetime]]) -> Optional[str]:
    """Formats a date or datetime as 'DD Month YYYY' (e.g., '11 October 2026')."""
    if d is None:
        return None
    if isinstance(d, datetime):
        d = to_gym_timezone(d).date()
    # Format e.g. '11 October 2026'
    return d.strftime("%d %B %Y")


def get_weekday(d: Optional[Union[date, datetime]]) -> Optional[str]:
    """Returns the full weekday name (e.g., 'Monday', 'Tuesday', 'Sunday')."""
    if d is None:
        return None
    if isinstance(d, datetime):
        d = to_gym_timezone(d).date()
    return d.strftime("%A")


def format_month_name(year: int, month: int) -> str:
    """Returns formatted Month Year (e.g., 'October 2026')."""
    try:
        d = date(year, month, 1)
        return d.strftime("%B %Y")
    except Exception:
        return f"{year}-{month:02d}"

