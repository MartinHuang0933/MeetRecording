"""In-memory log storage with a custom logging handler."""

import logging
from collections import deque
from datetime import datetime

MAX_LOG_ENTRIES = 2000


class LogEntry:
    __slots__ = ("timestamp", "level", "name", "message")

    def __init__(self, timestamp: str, level: str, name: str, message: str):
        self.timestamp = timestamp
        self.level = level
        self.name = name
        self.message = message


# Global in-memory log buffer (bounded deque)
log_buffer: deque[LogEntry] = deque(maxlen=MAX_LOG_ENTRIES)


class InMemoryHandler(logging.Handler):
    """Logging handler that stores records in an in-memory deque."""

    def emit(self, record: logging.LogRecord) -> None:
        entry = LogEntry(
            timestamp=datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            level=record.levelname,
            name=record.name,
            message=self.format(record),
        )
        log_buffer.append(entry)


def get_logs(level_filter: str = "", keyword: str = "", limit: int = 500) -> list[LogEntry]:
    """Retrieve logs with optional filtering."""
    results = []
    for entry in reversed(log_buffer):
        if level_filter and entry.level != level_filter.upper():
            continue
        if keyword and keyword.lower() not in entry.message.lower():
            continue
        results.append(entry)
        if len(results) >= limit:
            break
    return results


def clear_logs() -> int:
    """Clear all logs. Returns the number of entries cleared."""
    count = len(log_buffer)
    log_buffer.clear()
    return count
