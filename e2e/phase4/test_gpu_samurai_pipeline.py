import os
import time
from pathlib import Path

import pytest
import requests

from query.utils import extract_results, first_result

from conftest import object_exists


def _created_id(payload) -> str:
    row = first_result(payload)
    assert row and row.get("id")
    return str(row["id"])


def _rows(db, sql: str, vars=None):
    return extract_results(db.query(sql, vars or {}))


def _wait_for(predicate, *, timeout: int, interval: int = 10, label: str):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        last = predicate()
        if last:
            return last
        time.sleep(interval)
    raise AssertionError(f"Timed out waiting for {label}; last={last!r}")


def test_real_samurai_ulr_gpu_pipeline_to_hls_and_ui(db, s3, fixture_video: Path):
    timeout = int(os.getenv("PHASE4_TIMEOUT_SECONDS", "3600"))
    require_schema_json = os.getenv("PHASE4_REQUIRE_SCHEMA_JSON", "0").lower() in {"1", "true", "yes", "on"}
    dataset = f"phase4-gpu-{int(time.time())}"
    video_key = f"{dataset}/input/test-video.mp4"

    upload = s3.upload_file_as(str(fixture_video), video_key)
    assert upload.key == video_key
    assert object_exists(s3, video_key) is True

    file_id = _created_id(
        db.query(
            """
            CREATE file CONTENT {
                dataset: $DATASET,
                key: $KEY,
                name: 'test-video.mp4',
                mime: 'video/mp4',
                size: $SIZE,
                bucket: $BUCKET,
                encode: 'video-none',
                dead: false,
                uploadedAt: time::now(),
                meta: { phase: 'phase4' }
            };
            """,
            {
                "DATASET": dataset,
                "KEY": video_key,
                "SIZE": fixture_video.stat().st_size,
                "BUCKET": s3.bucket,
            },
        )
    )

    db.query(
        """
        CREATE annotation CONTENT {
            dataset: $DATASET,
            file: <record> $FILE,
            category: 'sam2_key_bbox',
            label: 'object',
            x1: 0.35,
            y1: 0.35,
            x2: 0.65,
            y2: 0.65,
            createdAt: time::now()
        };
        """,
        {"DATASET": dataset, "FILE": file_id},
    )

    job_id = _created_id(
        db.query(
            """
            CREATE inference_job CONTENT {
                name: $NAME,
                dead: false,
                status: 'ProcessWaiting',
                taskType: 'one-shot-object-detection',
                model: 'samurai-ulr',
                modelSource: 'internet',
                datasets: [$DATASET],
                createdAt: time::now(),
                updatedAt: time::now()
            };
            """,
            {"NAME": f"phase4-samurai-{int(time.time())}", "DATASET": dataset},
        )
    )

    def completed_job():
        row = first_result(db.query("SELECT status, progress FROM inference_job WHERE id = <record> $JOB LIMIT 1;", {"JOB": job_id}))
        if row and row.get("status") == "Faild":
            raise AssertionError(f"GPU inference job failed early: {row}")
        return row if row and row.get("status") == "Completed" else None

    job = _wait_for(completed_job, timeout=timeout, interval=15, label="samurai inference completion")
    assert job["status"] == "Completed"
    steps = {s.get("key"): s.get("state") for s in (job.get("progress") or {}).get("steps", []) if isinstance(s, dict)}
    for key in ["download", "preprocess", "sam2", "dataset_export", "rtdetr_train", "rtdetr_infer", "postprocess", "upload"]:
        assert steps.get(key) == "completed"

    results = _rows(db, "SELECT * FROM inference_result WHERE job = <record> $JOB;", {"JOB": job_id})
    artifacts = {((r.get("meta") or {}).get("artifact")): r for r in results}
    assert "plot_video" in artifacts
    assert "results_parquet" in artifacts
    if require_schema_json:
        assert "schema_json" in artifacts

    for result in results:
        assert object_exists(s3, result["key"]) is True

    plot_result_id = str(artifacts["plot_video"]["id"])

    def hls_ready():
        playlists = _rows(db, "SELECT * FROM hls_playlist WHERE file = <record> $FILE;", {"FILE": plot_result_id})
        segments = _rows(db, "SELECT * FROM hls_segment WHERE file = <record> $FILE;", {"FILE": plot_result_id})
        return {"playlists": playlists, "segments": segments} if playlists and segments else None

    hls = _wait_for(hls_ready, timeout=timeout, interval=15, label="HLS playlist and segments for inference video")
    for row in [*hls["playlists"], *hls["segments"]]:
        assert object_exists(s3, row["key"]) is True

    base_url = os.getenv("BASE_URL", "http://cloud-ui:3000")
    for path in ["/api/status", "/inference/opened-job", "/inference/opened-job/analysis"]:
        response = requests.get(f"{base_url}{path}", timeout=30)
        assert response.status_code == 200
