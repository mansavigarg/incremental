"""Rate limiting and request logging shared by all HTTP routes."""

from collections import defaultdict, deque
from pathlib import Path
from time import perf_counter


class SlidingWindowRateLimiter:
    def __init__(self, maximum_requests, window_seconds):
        self.maximum_requests = maximum_requests
        self.window_seconds = window_seconds
        self.request_times = defaultdict(deque)

    def is_allowed(self, client_key, current_time):
        times = self.request_times[client_key]
        while times and times[0] <= current_time - self.window_seconds:
            times.popleft()
        if len(times) >= self.maximum_requests:
            return False
        times.append(current_time)
        return True


class RequestLogger:
    def __init__(self, log_file_path):
        self.log_file_path = Path(log_file_path)
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)

    async def __call__(self, request, call_next):
        started = perf_counter()
        response = await call_next(request)
        milliseconds = (perf_counter() - started) * 1000
        with self.log_file_path.open("a", encoding="utf-8") as log:
            log.write(f"{request.method} {request.url.path} {response.status_code} {milliseconds:.1f}ms\n")
        return response
