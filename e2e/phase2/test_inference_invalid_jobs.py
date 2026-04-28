import pytest

from ml_inference_manager import MLInferenceRunner
from query.utils import first_result


def _created_id(payload) -> str:
    row = first_result(payload)
    assert row and row.get("id")
    return str(row["id"])


def _create_job(db, datasets):
    return _created_id(
        db.query(
            "CREATE inference_job CONTENT { name: $NAME, dead: false, status: 'ProcessWaiting', taskType: 'one-shot-object-detection', model: 'fake-model', modelSource: 'internet', datasets: $DATASETS, createdAt: time::now(), updatedAt: time::now() };",
            {"NAME": f"job-{len(datasets)}", "DATASETS": datasets},
        )
    )


def _create_file(db, *, dataset: str, name: str, mime: str, key: str):
    return _created_id(
        db.query(
            "CREATE file CONTENT { dataset: $DATASET, name: $NAME, mime: $MIME, key: $KEY, encode: 'video-none', dead: false };",
            {"DATASET": dataset, "NAME": name, "MIME": mime, "KEY": key},
        )
    )


@pytest.fixture
def runner(db, s3):
    return MLInferenceRunner(interval=0)


def test_inference_runner_rejects_job_without_dataset(db, runner):
    job_id = _create_job(db, [])

    with pytest.raises(ValueError, match="exactly one dataset"):
        runner._get_single_video_record(job_id)


def test_inference_runner_rejects_multiple_datasets(db, runner):
    job_id = _create_job(db, ["ds-a", "ds-b"])

    with pytest.raises(ValueError, match="Only one dataset"):
        runner._get_single_video_record(job_id)


def test_inference_runner_rejects_dataset_without_video(db, runner):
    _create_file(db, dataset="image-ds", name="image.jpg", mime="image/jpeg", key="image.jpg")
    job_id = _create_job(db, ["image-ds"])

    with pytest.raises(ValueError, match="No video file"):
        runner._get_single_video_record(job_id)


def test_inference_runner_rejects_dataset_with_multiple_videos(db, runner):
    _create_file(db, dataset="multi-video-ds", name="a.mp4", mime="video/mp4", key="a.mp4")
    _create_file(db, dataset="multi-video-ds", name="b.mp4", mime="video/mp4", key="b.mp4")
    job_id = _create_job(db, ["multi-video-ds"])

    with pytest.raises(ValueError, match="Multiple video files"):
        runner._get_single_video_record(job_id)


def test_inference_runner_accepts_single_video_dataset(db, runner):
    file_id = _create_file(db, dataset="single-video-ds", name="video.mp4", mime="video/mp4", key="video.mp4")
    job_id = _create_job(db, ["single-video-ds"])

    video = runner._get_single_video_record(job_id)

    assert video == {
        "dataset": "single-video-ds",
        "file_id": file_id,
        "file_name": "video.mp4",
        "key": "video.mp4",
    }
