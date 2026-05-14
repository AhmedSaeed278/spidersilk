"""End-to-end-ish tests using moto's in-memory S3."""

import boto3
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws

BUCKET = "spidersilk-test"


@pytest.fixture(autouse=True)
def _aws_env(monkeypatch, tmp_path):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("SPIDERSILK_S3_BUCKET", BUCKET)
    monkeypatch.setenv("SPIDERSILK_AWS_REGION", "us-east-1")
    monkeypatch.setenv("SPIDERSILK_PUBLIC_DIR", str(tmp_path / "public"))
    from spidersilk import config, s3_client
    config.get_settings.cache_clear()
    s3_client._client.cache_clear()


@pytest.fixture
def client():
    with mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket=BUCKET)
        from spidersilk.main import app
        with TestClient(app) as c:
            yield c


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.text == "ok"


def test_index(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Spidersilk" in r.text


def test_upload_and_list(client):
    csv_body = b'"1","Item One","10.0000"\n"2","Item Two","20.5000"\n'
    r = client.post("/upload", files={"file": ("soh.csv", csv_body, "text/csv")})
    assert r.status_code == 200, r.text
    assert "Item One" in r.text

    r = client.get("/files")
    assert r.status_code == 200
    assert "soh.csv" in r.text


def test_rejects_empty_upload(client):
    r = client.post("/upload", files={"file": ("empty.csv", b"", "text/csv")})
    assert r.status_code == 400
