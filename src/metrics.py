"""Minimal Prometheus-style metrics without the prometheus_client dependency.

Only counters for now (requests by method/status, deliveries by status).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from threading import Lock


class Counter:
    def __init__(self, name: str, help_text: str, label_names: Iterable[str] = ()):
        self.name = name
        self.help = help_text
        self.label_names = tuple(label_names)
        self._values: dict[tuple[str, ...], float] = defaultdict(float)
        self._lock = Lock()

    def labels(self, **kwargs: str) -> Counter._Bound:
        key = tuple(kwargs.get(n, "") for n in self.label_names)
        return Counter._Bound(self, key)

    def inc(self, amount: float = 1.0) -> None:
        with self._lock:
            self._values[()] += amount

    def render(self) -> str:
        lines = [f"# HELP {self.name} {self.help}", f"# TYPE {self.name} counter"]
        if self._values:
            for key, value in self._values.items():
                if key:
                    labels = ",".join(
                        f'{name}="{val}"' for name, val in zip(self.label_names, key, strict=False)
                    )
                    lines.append(f"{self.name}{{{labels}}} {value}")
                else:
                    lines.append(f"{self.name} {value}")
        return "\n".join(lines)

    class _Bound:
        def __init__(self, parent: Counter, key: tuple[str, ...]):
            self._parent = parent
            self._key = key

        def inc(self, amount: float = 1.0) -> None:
            with self._parent._lock:
                self._parent._values[self._key] += amount


REQUESTS = Counter(
    "emaildigest_http_requests_total",
    "Count of HTTP responses served",
    ("method", "status"),
)
DELIVERIES = Counter(
    "emaildigest_deliveries_total",
    "Count of digest deliveries completed",
    ("status",),
)

_ALL: tuple[Counter, ...] = (REQUESTS, DELIVERIES)


def prometheus_output() -> str:
    return "\n\n".join(c.render() for c in _ALL) + "\n"
