import time
from collections import defaultdict, deque

from app.contracts.common import ErrorCode
from app.errors import AppError

WINDOW_S = 3600


class RateLimiter:
    """In-memory sliding window, good enough for a single-process demo stand"""

    def __init__(self) -> None:
        self._hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)

    def _window(self, key: str, action: str, now: float) -> deque[float]:
        window = self._hits[(key, action)]
        while window and now - window[0] > WINDOW_S:
            window.popleft()
        return window

    def ensure_below(self, key: str, action: str, limit_per_hour: int) -> None:
        """Raise 429 if the limit is reached, without counting this call"""
        now = time.monotonic()
        window = self._window(key, action, now)
        if len(window) >= limit_per_hour:
            raise AppError(
                429,
                ErrorCode.RATE_LIMITED,
                f"Too many '{action}' requests, try again later",
                {"retry_after_s": int(WINDOW_S - (now - window[0]))},
            )

    def record(self, key: str, action: str) -> None:
        self._window(key, action, time.monotonic()).append(time.monotonic())

    def check(self, key: str, action: str, limit_per_hour: int) -> None:
        self.ensure_below(key, action, limit_per_hour)
        self.record(key, action)
