import time
import psutil
import os
from datetime import datetime
from typing import Optional


class HealthMetrics:
    def __init__(self):
        self._metrics = {}
        self._start_time = time.time()

    def record(self, name: str, value: float) -> None:
        now = datetime.now().isoformat()
        if name not in self._metrics:
            self._metrics[name] = []
        self._metrics[name].append((now, value))
        if len(self._metrics[name]) > 1000:
            self._metrics[name] = self._metrics[name][-1000:]

    def get_since(self, since: str) -> dict:
        result = {}
        for name, values in self._metrics.items():
            result[name] = [v for t, v in values if t >= since]
        return result

    def get_recent(self, name: str, count: int = 5) -> list:
        values = self._metrics.get(name, [])
        return [v for _, v in values[-count:]]


class HealthChecker:
    def __init__(self, metrics: HealthMetrics = None):
        self.metrics = metrics or HealthMetrics()
        self._start_time = time.time()

    def check(self) -> dict:
        checks = {
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": int(time.time() - self._start_time),
        }
        try:
            cpu = psutil.cpu_percent(interval=0.1)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage(os.path.dirname(os.path.dirname(__file__)))
            checks["cpu_percent"] = cpu
            checks["ram_percent"] = ram.percent
            checks["ram_available_mb"] = ram.available // (1024 * 1024)
            checks["disk_percent"] = disk.percent
            checks["disk_free_gb"] = disk.free // (1024**3)
            checks["status"] = "healthy" if cpu < 90 and ram.percent < 90 else "degraded"
        except Exception as e:
            checks["status"] = "unknown"
            checks["error"] = str(e)

        if self.metrics:
            self.metrics.record("health_check", 1 if checks.get("status") == "healthy" else 0)

        return checks


_start_time = time.time()
_metrics = HealthMetrics()
_checker = HealthChecker(_metrics)


def get_health() -> dict:
    return _checker.check()


def record_metric(name: str, value: float) -> None:
    _metrics.record(name, value)


def get_metrics(since: str = "") -> dict:
    return _metrics.get_since(since)
