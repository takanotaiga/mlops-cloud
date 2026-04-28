import os
import tempfile
import time
from pathlib import Path

import pandas as pd
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


def _meta(row: dict) -> dict:
    meta = row.get("meta")
    return meta if isinstance(meta, dict) else {}


def _artifact_description(row: dict) -> str:
    return str(_meta(row).get("description") or "")


def _download_parquet(s3, key: str) -> pd.DataFrame:
    with tempfile.NamedTemporaryFile(suffix=".parquet") as tmp:
        s3.s3.download_file(s3.bucket, key, tmp.name)
        return pd.read_parquet(tmp.name)


def _assert_bbox_rows(
    df: pd.DataFrame,
    *,
    label: str,
    source: str,
    min_positive_ratio: float = 0.95,
) -> None:
    assert not df.empty, f"{source} parquet must contain at least one detection row"
    for column in ["frame_index", "label", "x", "y", "w", "h"]:
        assert column in df.columns, f"{source} parquet is missing column: {column}"
    assert set(df["label"].dropna().astype(str)) == {label}
    assert (df["frame_index"].astype(int) >= 0).all()
    positive_bbox = (df["w"].astype(float) > 0) & (df["h"].astype(float) > 0)
    assert positive_bbox.any(), f"{source} parquet has no positive-size bbox rows"
    assert positive_bbox.mean() >= min_positive_ratio, (
        f"{source} positive bbox ratio is too low: "
        f"{positive_bbox.mean():.3f} < {min_positive_ratio:.3f}"
    )


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
    artifact_names = {str(_meta(r).get("artifact")) for r in results}
    assert "plot_video" in artifact_names
    assert "results_parquet" in artifact_names
    if require_schema_json:
        assert "schema_json" in artifact_names

    for result in results:
        assert object_exists(s3, result["key"]) is True

    sam2_parquets = [
        r for r in results
        if _meta(r).get("artifact") == "results_parquet"
        and "SAM2" in _artifact_description(r)
    ]
    assert sam2_parquets, f"SAM2 results parquet was not registered: {results!r}"
    sam2_df = _download_parquet(s3, sam2_parquets[0]["key"])
    _assert_bbox_rows(sam2_df, label="object", source="SAM2", min_positive_ratio=0.90)

    rtdetr_parquets = [
        r for r in results
        if _meta(r).get("artifact") == "results_parquet"
        and "最終推論結果" in _artifact_description(r)
    ]
    assert rtdetr_parquets, f"RT-DETR final parquet was not registered: {results!r}"
    rtdetr_df = _download_parquet(s3, rtdetr_parquets[0]["key"])
    _assert_bbox_rows(rtdetr_df, label="object", source="RT-DETR", min_positive_ratio=0.90)
    assert "conf" in rtdetr_df.columns
    assert rtdetr_df["conf"].notna().all()
    assert (rtdetr_df["conf"].astype(float) >= 0).all()

    rtdetr_plot_videos = [
        r for r in results
        if _meta(r).get("artifact") == "plot_video"
        and "RT-DETR" in _artifact_description(r)
    ]
    assert rtdetr_plot_videos, f"RT-DETR plot video was not registered: {results!r}"
    plot_result_id = str(rtdetr_plot_videos[0]["id"])

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
