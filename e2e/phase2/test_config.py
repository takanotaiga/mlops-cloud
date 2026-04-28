from backend_module.config import load_s3_config, load_surreal_config


def test_surreal_config_prefers_compose_env(monkeypatch):
    monkeypatch.setenv("SURREAL_URL", "ws://database:8000/rpc")
    monkeypatch.setenv("SURREAL_NS", "phase2")
    monkeypatch.setenv("SURREAL_DB", "backend")
    monkeypatch.setenv("SURREAL_USER", "root")
    monkeypatch.setenv("SURREAL_PASS", "secret")
    monkeypatch.setenv("SURREAL_ENDPOINT", "ws://legacy:8000/rpc")

    assert load_surreal_config() == {
        "endpoint_url": "ws://database:8000/rpc",
        "namespace": "phase2",
        "database": "backend",
        "username": "root",
        "password": "secret",
    }


def test_surreal_config_uses_legacy_fallbacks(monkeypatch):
    for key in ["SURREAL_URL", "SURREAL_NS", "SURREAL_DB", "SURREAL_USER", "SURREAL_PASS"]:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("SURREAL_ENDPOINT", "ws://legacy:8000/rpc")
    monkeypatch.setenv("SURREAL_NAMESPACE", "legacy_ns")
    monkeypatch.setenv("SURREAL_DATABASE", "legacy_db")
    monkeypatch.setenv("SURREAL_USERNAME", "legacy_user")
    monkeypatch.setenv("SURREAL_PASSWORD", "legacy_pass")

    assert load_surreal_config() == {
        "endpoint_url": "ws://legacy:8000/rpc",
        "namespace": "legacy_ns",
        "database": "legacy_db",
        "username": "legacy_user",
        "password": "legacy_pass",
    }


def test_s3_config_prefers_minio_env(monkeypatch):
    monkeypatch.setenv("MINIO_ENDPOINT_INTERNAL", "http://object-storage:9000")
    monkeypatch.setenv("MINIO_REGION", "ap-northeast-1")
    monkeypatch.setenv("MINIO_ACCESS_KEY_ID", "access")
    monkeypatch.setenv("MINIO_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setenv("MINIO_BUCKET", "bucket")
    monkeypatch.setenv("MINIO_FORCE_PATH_STYLE", "false")
    monkeypatch.setenv("S3_ENDPOINT", "http://legacy:9000")

    conf = load_s3_config()

    assert conf["endpoint_url"] == "http://object-storage:9000"
    assert conf["region_name"] == "ap-northeast-1"
    assert conf["access_key"] == "access"
    assert conf["secret_key"] == "secret"
    assert conf["bucket"] == "bucket"
    assert conf["addressing_style"] == "virtual"


def test_s3_config_uses_legacy_fallbacks(monkeypatch):
    for key in [
        "MINIO_ENDPOINT_INTERNAL",
        "MINIO_ACCESS_KEY_ID",
        "MINIO_SECRET_ACCESS_KEY",
        "MINIO_BUCKET",
    ]:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("S3_ENDPOINT", "http://legacy:9000")
    monkeypatch.setenv("S3_ACCESS_KEY", "legacy_access")
    monkeypatch.setenv("S3_SECRET_KEY", "legacy_secret")
    monkeypatch.setenv("S3_BUCKET", "legacy_bucket")

    conf = load_s3_config()

    assert conf["endpoint_url"] == "http://legacy:9000"
    assert conf["access_key"] == "legacy_access"
    assert conf["secret_key"] == "legacy_secret"
    assert conf["bucket"] == "legacy_bucket"
