import time
from collections import defaultdict, deque

from app.contracts.common import ErrorCode
from app.errors import AppError


class RateLimiter:
    """In-memory sliding window, good enough for a single-process demo stand"""

    def __init__(self) -> None:
        self._hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)

    def check(self, user_id: str, action: str, limit_per_hour: int) -> None:
        now = time.monotonic()
        window = self._hits[(user_id, action)]
        while window and now - window[0] > 3600:
            window.popleft()
        if len(window) >= limit_per_hour:
            raise AppError(
                429,
                ErrorCode.RATE_LIMITED,
                f"Too many '{action}' requests, try again later",
                {"retry_after_s": int(3600 - (now - window[0]))},
            )
        window.append(now)
