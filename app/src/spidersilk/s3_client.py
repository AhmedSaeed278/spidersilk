"""Thin S3 wrapper. Uses the default boto3 credential chain (IRSA in-cluster)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache

import boto3
from botocore.config import Config

from .config import get_settings


@dataclass(frozen=True, slots=True)
class StoredObject:
    key: str
    size: int
    last_modified: datetime


@lru_cache(maxsize=1)
def _client():
    s = get_settings()
    cfg = Config(region_name=s.aws_region, retries={"max_attempts": 5, "mode": "standard"})
    kwargs: dict = {"config": cfg}
    if s.s3_endpoint_url:
        kwargs["endpoint_url"] = s.s3_endpoint_url
    return boto3.client("s3", **kwargs)


def put_object(key: str, data: bytes, content_type: str = "text/csv") -> None:
    s = get_settings()
    _client().put_object(
        Bucket=s.s3_bucket,
        Key=key,
        Body=data,
        ContentType=content_type,
        ServerSideEncryption="AES256",
    )


def list_objects(prefix: str | None = None, limit: int = 100) -> list[StoredObject]:
    s = get_settings()
    pfx = prefix if prefix is not None else s.s3_prefix
    paginator = _client().get_paginator("list_objects_v2")
    out: list[StoredObject] = []
    pages = paginator.paginate(
        Bucket=s.s3_bucket, Prefix=pfx, PaginationConfig={"MaxItems": limit}
    )
    for page in pages:
        for obj in page.get("Contents", []):
            out.append(
                StoredObject(
                    key=obj["Key"],
                    size=int(obj["Size"]),
                    last_modified=obj["LastModified"],
                )
            )
    out.sort(key=lambda o: o.last_modified, reverse=True)
    return out


def get_object(key: str) -> bytes:
    s = get_settings()
    resp = _client().get_object(Bucket=s.s3_bucket, Key=key)
    return resp["Body"].read()
