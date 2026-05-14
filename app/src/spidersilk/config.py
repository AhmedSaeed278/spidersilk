from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, loaded from env vars (12-factor)."""

    model_config = SettingsConfigDict(env_prefix="SPIDERSILK_", env_file=None)

    app_name: str = "spidersilk"
    environment: str = "dev"
    log_level: str = "INFO"

    # S3
    s3_bucket: str = Field(default="spidersilk-csv-archive-dev")
    s3_prefix: str = "uploads/"
    aws_region: str = "us-east-1"
    # When set, used as endpoint_url for boto3 (LocalStack / MinIO testing).
    s3_endpoint_url: str | None = None

    # Upload constraints
    max_upload_bytes: int = 10 * 1024 * 1024  # 10 MiB
    allowed_content_types: tuple[str, ...] = (
        "text/csv",
        "application/vnd.ms-excel",
        "application/octet-stream",
    )

    # Shared volume path (mounted between nginx and the app)
    public_dir: str = "/public"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
