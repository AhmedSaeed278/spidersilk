output "bucket_name" {
  description = "Name of the CSV archive S3 bucket."
  value       = aws_s3_bucket.csv_archive.bucket
}

output "bucket_arn" {
  description = "ARN of the CSV archive S3 bucket."
  value       = aws_s3_bucket.csv_archive.arn
}

output "app_role_arn" {
  description = "ARN of the IRSA role the Spidersilk app assumes. Empty if create_irsa_role = false."
  value       = try(aws_iam_role.app[0].arn, "")
}

output "app_policy_arn" {
  description = "ARN of the IAM policy granting S3 access."
  value       = aws_iam_policy.app.arn
}
