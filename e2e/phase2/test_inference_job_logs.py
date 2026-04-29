from backend_module.job_log import capture_job_logs
from query.inference_job_log_query import append_job_log, count_job_logs, list_job_log_archives, list_job_logs
from query.utils import first_result


def _created_id(payload) -> str:
    row = first_result(payload)
    assert row and row.get("id")
    return str(row["id"])


def test_inference_job_logs_are_scoped_by_job(db):
    job_a = _created_id(
        db.query(
            """
            CREATE inference_job CONTENT {
                name: 'log-job-a',
                dead: false,
                status: 'ProcessRunning',
                taskType: 'one-shot-object-detection',
                model: 'fake',
                modelSource: 'internet',
                datasets: ['ds-a'],
                createdAt: time::now(),
                updatedAt: time::now()
            };
            """
        )
    )
    job_b = _created_id(
        db.query(
            """
            CREATE inference_job CONTENT {
                name: 'log-job-b',
                dead: false,
                status: 'ProcessRunning',
                taskType: 'one-shot-object-detection',
                model: 'fake',
                modelSource: 'internet',
                datasets: ['ds-b'],
                createdAt: time::now(),
                updatedAt: time::now()
            };
            """
        )
    )

    append_job_log(db, job_id=job_a, source="mlx", stream="stdout", message="job-a line", seq=1)
    append_job_log(db, job_id=job_b, source="mlx", stream="stdout", message="job-b line", seq=1)

    logs = list_job_logs(db, job_id=job_a)
    assert [line["message"] for line in logs] == ["job-a line"]


def test_capture_job_logs_persists_stdout_and_stderr(db):
    job_id = _created_id(
        db.query(
            """
            CREATE inference_job CONTENT {
                name: 'captured-log-job',
                dead: false,
                status: 'ProcessRunning',
                taskType: 'one-shot-object-detection',
                model: 'fake',
                modelSource: 'internet',
                datasets: ['ds-a'],
                createdAt: time::now(),
                updatedAt: time::now()
            };
            """
        )
    )

    with capture_job_logs(db, job_id=job_id, source="mlx"):
        print("stdout line")
        import sys
        print("stderr line", file=sys.stderr)

    logs = list_job_logs(db, job_id=job_id)
    assert [(line["source"], line["stream"], line["message"]) for line in logs] == [
        ("mlx", "stdout", "stdout line"),
        ("mlx", "stderr", "stderr line"),
    ]


def test_inference_job_logs_return_more_than_legacy_ui_cap(db):
    job_id = _created_id(
        db.query(
            """
            CREATE inference_job CONTENT {
                name: 'large-log-job',
                dead: false,
                status: 'ProcessRunning',
                taskType: 'one-shot-object-detection',
                model: 'fake',
                modelSource: 'internet',
                datasets: ['ds-a'],
                createdAt: time::now(),
                updatedAt: time::now()
            };
            """
        )
    )

    for index in range(600):
        append_job_log(
            db,
            job_id=job_id,
            source="mlx",
            stream="stdout",
            message=f"line-{index}",
            seq=index,
        )

    logs = list_job_logs(db, job_id=job_id)
    assert len(logs) == 600
    assert logs[0]["message"] == "line-0"
    assert logs[-1]["message"] == "line-599"


def test_inference_job_logs_archive_to_s3_in_chunks_and_keep_db_tail(db, s3, tmp_path):
    job_id = _created_id(
        db.query(
            """
            CREATE inference_job CONTENT {
                name: 'archived-log-job',
                dead: false,
                status: 'ProcessRunning',
                taskType: 'one-shot-object-detection',
                model: 'fake',
                modelSource: 'internet',
                datasets: ['ds-a'],
                createdAt: time::now(),
                updatedAt: time::now()
            };
            """
        )
    )

    for index in range(25):
        append_job_log(
            db,
            job_id=job_id,
            source="mlx",
            stream="stdout",
            message=f"line-{index}",
            seq=index,
            archive_uploader=s3,
            retention=10,
            archive_chunk_size=10,
        )

    assert count_job_logs(db, job_id=job_id) == 5
    assert [row["message"] for row in list_job_logs(db, job_id=job_id)] == [f"line-{i}" for i in range(20, 25)]

    archives = list_job_log_archives(db, job_id=job_id)
    assert len(archives) == 2
    assert [archive["rowCount"] for archive in archives] == [10, 10]

    restored_lines = []
    for index, archive in enumerate(archives):
        assert archive["key"].endswith(".log")
        local_path = tmp_path / f"archive-{index}.log"
        downloaded = s3.download_file(archive["key"], str(local_path))
        assert downloaded.local_path == str(local_path)
        restored_lines.extend(local_path.read_text(encoding="utf-8").splitlines())

    assert len(restored_lines) == 20
    for index, line in enumerate(restored_lines):
        assert f"[# {index}]" not in line
        assert f"[#{index}]" in line
        assert f"line-{index}" in line
