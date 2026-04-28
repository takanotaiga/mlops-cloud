from pathlib import Path
import os
import sys
import time
from typing import Iterable

import pytest
from botocore.exceptions import ClientError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend_module.config import load_s3_config, load_surreal_config
from backend_module.database import DataBaseManager
from backend_module.object_storage import MinioS3Uploader

TABLES = [
    "annotation",
    "encoded_segment",
    "hls_job",
    "hls_playlist",
    "hls_segment",
    "inference_result",
    "inference_job",
    "label",
    "merge_group",
    "file",
]


def connect_db() -> DataBaseManager:
    conf = load_surreal_config()
    last_error = None
    for _ in range(90):
        try:
            db = DataBaseManager(
                endpoint_url=conf["endpoint_url"],
                username=conf["username"],
                password=conf["password"],
                namespace=conf["namespace"],
                database=conf["database"],
            )
            db.query("RETURN true;")
            return db
        except Exception as exc:
            last_error = exc
            time.sleep(1)
    raise RuntimeError(f"SurrealDB did not become ready: {last_error}")


def connect_s3() -> MinioS3Uploader:
    conf = load_s3_config()
    last_error = None
    for _ in range(90):
        try:
            s3 = MinioS3Uploader(
                endpoint_url=conf["endpoint_url"],
                access_key=conf["access_key"],
                secret_key=conf["secret_key"],
                bucket=conf["bucket"],
                region_name=conf["region_name"],
                multipart_threshold_bytes=conf["multipart_threshold_bytes"],
                multipart_chunksize_bytes=conf["multipart_chunksize_bytes"],
                part_concurrency=conf["part_concurrency"],
                addressing_style=conf["addressing_style"],
            )
            s3.s3.head_bucket(Bucket=s3.bucket)
            return s3
        except Exception as exc:
            last_error = exc
            time.sleep(1)
    raise RuntimeError(f"MinIO did not become ready: {last_error}")


@pytest.fixture(scope="session")
def db() -> DataBaseManager:
    return connect_db()


@pytest.fixture(scope="session")
def s3() -> MinioS3Uploader:
    return connect_s3()


@pytest.fixture(scope="session")
def fixture_video() -> Path:
    path = Path(os.getenv("PHASE4_VIDEO_FIXTURE", "/fixtures/test-video.mp4"))
    if not path.exists():
        pytest.skip(f"Phase4 video fixture is missing: {path}")
    return path


def empty_bucket(s3: MinioS3Uploader) -> None:
    while True:
        page = s3.s3.list_objects_v2(Bucket=s3.bucket)
        objects = [{"Key": obj["Key"]} for obj in page.get("Contents", []) if obj.get("Key")]
        if not objects:
            return
        s3.s3.delete_objects(Bucket=s3.bucket, Delete={"Objects": objects})


def reset_tables(db: DataBaseManager, tables: Iterable[str] = TABLES) -> None:
    for table in tables:
        db.query(f"DELETE {table};")


@pytest.fixture(autouse=True)
def clean_state(db: DataBaseManager, s3: MinioS3Uploader):
    reset_tables(db)
    empty_bucket(s3)
    yield
    reset_tables(db)
    empty_bucket(s3)


def object_exists(s3: MinioS3Uploader, key: str) -> bool:
    try:
        s3.s3.head_object(Bucket=s3.bucket, Key=key)
        return True
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code in {"404", "NoSuchKey", "NotFound"}:
            return False
        raise
