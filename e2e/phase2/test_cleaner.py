from cleaner_manager import TaskRunner
from query.utils import extract_results, first_result

from conftest import object_exists


def _created_id(payload) -> str:
    row = first_result(payload)
    assert row and row.get("id")
    return str(row["id"])


def test_cleaner_removes_dead_file_records_and_s3_objects(db, s3):
    key = "dead/original.jpg"
    thumb_key = "dead/thumb.jpg"
    s3.s3.put_object(Bucket=s3.bucket, Key=key, Body=b"original")
    s3.s3.put_object(Bucket=s3.bucket, Key=thumb_key, Body=b"thumb")
    file_id = _created_id(
        db.query(
            "CREATE file CONTENT { dataset: 'dead-dataset', name: 'original.jpg', mime: 'image/jpeg', key: $KEY, thumbKey: $THUMB_KEY, dead: true };",
            {"KEY": key, "THUMB_KEY": thumb_key},
        )
    )

    TaskRunner(interval=0).task_main()

    rows = extract_results(db.query("SELECT * FROM file WHERE id = <record> $ID;", {"ID": file_id}))
    assert rows == []
    assert object_exists(s3, key) is False
    assert object_exists(s3, thumb_key) is False


def test_cleaner_removes_orphan_annotation_records_and_s3_objects(db, s3):
    key = "orphan/annotation.json"
    s3.s3.put_object(Bucket=s3.bucket, Key=key, Body=b"{}")
    annotation_id = _created_id(
        db.query(
            "CREATE annotation SET key = $KEY, file = NONE, createdAt = time::now();",
            {"KEY": key},
        )
    )

    TaskRunner(interval=0).task_main()

    rows = extract_results(db.query("SELECT * FROM annotation WHERE id = <record> $ID;", {"ID": annotation_id}))
    assert rows == []
    assert object_exists(s3, key) is False
