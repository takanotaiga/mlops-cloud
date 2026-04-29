from types import SimpleNamespace

import hardware_metrics_manager as hm
from hardware_metrics_manager import HardwareMetricsManager
from query.utils import extract_results


def test_hardware_metric_insert_persists_cpu_and_gpu_shape(db):
    manager = HardwareMetricsManager(db, cleanup_interval_sec=999)
    manager._insert_metrics(
        {
            "cpu_percent": 12.5,
            "memory": {
                "total": 100,
                "available": 70,
                "used": 30,
                "free": 65,
                "percent": 30.0,
            },
            "load_average": [0.1, 0.2, 0.3],
        },
        [
            {
                "index": 0,
                "name": "Fake GPU",
                "utilization": {"gpu_percent": 45, "memory_percent": 20},
                "memory": {"total": 1000, "used": 200, "free": 800},
                "power_watts": 77.5,
                "temperature_c": 55,
                "fan_speed_percent": 40,
                "pcie": {"tx_kb_s": 10, "rx_kb_s": 20},
                "clocks_mhz": {"sm": 1500, "mem": 5000},
            }
        ],
    )

    rows = extract_results(db.query("SELECT * FROM hardware_metric;"))

    assert len(rows) == 1
    assert rows[0]["system"]["cpu_percent"] == 12.5
    assert rows[0]["system"]["memory"]["total"] == 100
    assert rows[0]["gpus"][0]["name"] == "Fake GPU"
    assert rows[0]["gpus"][0]["memory"]["total"] == 1000


def test_gather_system_metrics_contains_cpu_and_memory():
    metrics = hm._gather_system_metrics()

    assert isinstance(metrics["cpu_percent"], (int, float))
    assert metrics["cpu_percent"] >= 0
    assert metrics["memory"]["total"] > 0


def test_gather_gpu_metrics_collects_nvml_shape(monkeypatch):
    class FakeNvml:
        NVML_TEMPERATURE_GPU = 0
        NVML_PCIE_UTIL_TX_BYTES = 1
        NVML_PCIE_UTIL_RX_BYTES = 2
        NVML_CLOCK_SM = 3
        NVML_CLOCK_MEM = 4

        def nvmlInit(self):
            return None

        def nvmlShutdown(self):
            return None

        def nvmlDeviceGetCount(self):
            return 1

        def nvmlDeviceGetHandleByIndex(self, index):
            return f"gpu-{index}"

        def nvmlDeviceGetName(self, handle):
            return b"Fake NVML GPU"

        def nvmlDeviceGetUtilizationRates(self, handle):
            return SimpleNamespace(gpu=50, memory=25)

        def nvmlDeviceGetMemoryInfo(self, handle):
            return SimpleNamespace(total=1000, used=250, free=750)

        def nvmlDeviceGetTemperature(self, handle, sensor):
            return 60

        def nvmlDeviceGetFanSpeed(self, handle):
            return 35

        def nvmlDeviceGetPowerUsage(self, handle):
            return 80000

        def nvmlDeviceGetPcieThroughput(self, handle, counter):
            return 123

        def nvmlDeviceGetClockInfo(self, handle, clock):
            return 1500 if clock == self.NVML_CLOCK_SM else 5000

    monkeypatch.setattr(hm, "pynvml", FakeNvml())

    gpus = hm._gather_gpu_metrics()

    assert len(gpus) == 1
    assert gpus[0]["name"] == "Fake NVML GPU"
    assert gpus[0]["utilization"]["gpu_percent"] == 50
    assert gpus[0]["memory"]["total"] == 1000
    assert gpus[0]["power_watts"] == 80.0
