# Lifecycle: transition objects to GLACIER after N days, expire after M days.
# Noncurrent versions transition to GLACIER and expire on their own schedule.
resource "aws_s3_bucket_lifecycle_configuration" "csv_archive" {
  bucket = aws_s3_bucket.csv_archive.id

  depends_on = [aws_s3_bucket_versioning.csv_archive]

  rule {
    id     = "csv-archival"
    status = "Enabled"

    filter {} # apply to whole bucket

    transition {
      days          = var.glacier_transition_days
      storage_class = "GLACIER"
    }

    expiration {
      days = var.expire_days
    }

    noncurrent_version_transition {
      noncurrent_days = var.glacier_transition_days
      storage_class   = "GLACIER"
    }

    noncurrent_version_expiration {
      noncurrent_days = var.noncurrent_expire_days
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}
