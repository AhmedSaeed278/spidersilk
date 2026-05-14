data "aws_caller_identity" "current" {}

locals {
  bucket_name = var.bucket_name != "" ? var.bucket_name : "spidersilk-csv-archive-${var.environment}-${data.aws_caller_identity.current.account_id}"
}

# ---------------- S3 bucket -----------------------------------------------------
resource "aws_s3_bucket" "csv_archive" {
  bucket = local.bucket_name

  tags = {
    Name = local.bucket_name
  }
}

resource "aws_s3_bucket_ownership_controls" "csv_archive" {
  bucket = aws_s3_bucket.csv_archive.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_public_access_block" "csv_archive" {
  bucket                  = aws_s3_bucket.csv_archive.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "csv_archive" {
  bucket = aws_s3_bucket.csv_archive.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "csv_archive" {
  bucket = aws_s3_bucket.csv_archive.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# Deny all non-TLS access.
resource "aws_s3_bucket_policy" "csv_archive_tls" {
  bucket = aws_s3_bucket.csv_archive.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyInsecureTransport"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.csv_archive.arn,
          "${aws_s3_bucket.csv_archive.arn}/*"
        ]
        Condition = {
          Bool = { "aws:SecureTransport" = "false" }
        }
      }
    ]
  })
}
