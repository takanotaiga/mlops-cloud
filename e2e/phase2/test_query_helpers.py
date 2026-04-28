import pytest

from query.hls_job_query import InvalidJobTransition, set_hls_job_status
from query.ml_inference_job_query import set_inference_job_status
from query.utils import extract_results, first_result, rid_leaf


def test_query_response_helpers_accept_enveloped_and_raw_payloads():
    enveloped = [{"status": "OK", "result": [{"id": "file:one"}, {"id": "file:two"}]}]
    raw = [{"id": "file:raw"}]

    assert first_result(enveloped) == {"id": "file:one"}
    assert extract_results(enveloped) == [{"id": "file:one"}, {"id": "file:two"}]
    assert first_result(raw) == {"id": "file:raw"}
    assert extract_results(raw) == [{"id": "file:raw"}]
    assert first_result([]) is None
    assert extract_results([]) == []


def test_rid_leaf_handles_strings_and_recordish_objects():
    assert rid_leaf("file:abc") == "abc"
    assert rid_leaf("plain") == "plain"

    class Recordish:
        def __str__(self):
            return "inference_job:job-1"

    assert rid_leaf(Recordish()) == "job-1"


def _created_id(payload) -> str:
    row = first_result(payload)
    assert row and row.get("id")
    return str(row["id"])


def test_hls_job_status_transitions(db):
    file_id = _created_id(db.query("CREATE file CONTENT { dataset: 'video-ds', name: 'video.mp4', mime: 'video/mp4', key: 'video.mp4', encode: 'video-none', dead: false };"))
    job_id = _created_id(
        db.query(
            "CREATE hls_job CONTENT { file: <record> $FILE_ID, status: 'queued', created_at: time::now() };",
            {"FILE_ID": file_id},
        )
    )

    assert set_hls_job_status(db, job_id, "in_progress")["updated"] is True
    assert set_hls_job_status(db, job_id, "complete")["updated"] is True
    with pytest.raises(InvalidJobTransition):
        set_hls_job_status(db, job_id, "queued")


def test_inference_job_status_transitions(db):
    job_id = _created_id(
        db.query(
            "CREATE inference_job CONTENT { name: 'job', dead: false, status: 'ProcessWaiting', taskType: 'one-shot-object-detection', model: 'fake', modelSource: 'internet', datasets: ['ds-a'], createdAt: time::now(), updatedAt: time::now() };"
        )
    )

    assert set_inference_job_status(db, job_id, "ProcessRunning")["updated"] is True
    assert set_inference_job_status(db, job_id, "Completed")["updated"] is True
    with pytest.raises(ValueError, match="Invalid transition"):
        set_inference_job_status(db, job_id, "ProcessWaiting")
