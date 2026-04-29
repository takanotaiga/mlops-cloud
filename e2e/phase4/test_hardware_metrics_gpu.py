import time

from query.utils import extract_results


def _rows(db, sql: str, vars=None):
    return extract_results(db.query(sql, vars or {}))


def _wait_for(predicate, *, timeout: int, interval: int = 2, label: str):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        last = predicate()
        if last:
            return last
        time.sleep(interval)
    raise AssertionError(f"Timed out waiting for {label}; last={last!r}")


def test_hardware_metrics_records_cpu_and_gpu(db):
    def observed_metrics():
        rows = _rows(db, "SELECT * FROM hardware_metric ORDER BY ts DESC LIMIT 20;")
        cpu_rows = [
            row for row in rows
            if isinstance((row.get("system") or {}).get("cpu_percent"), (int, float))
            and ((row.get("system") or {}).get("memory") or {}).get("total", 0) > 0
        ]
        gpu_rows = [
            row for row in rows
            if any(
                gpu.get("name")
                and ((gpu.get("memory") or {}).get("total", 0) > 0)
                for gpu in (row.get("gpus") or [])
                if isinstance(gpu, dict)
            )
        ]
        return {"cpu": cpu_rows[0], "gpu": gpu_rows[0]} if cpu_rows and gpu_rows else None

    metrics = _wait_for(observed_metrics, timeout=120, label="CPU and GPU hardware metrics")
    assert metrics["cpu"]["system"]["cpu_percent"] >= 0
    assert len(metrics["gpu"]["gpus"]) >= 1
