# IRSA role: lets the Spidersilk pod sign requests to S3 without static keys.
# Requires the cluster's OIDC provider to have been created (kops handles this
# via `serviceAccountIssuerDiscovery`).

locals {
  irsa_sub = "system:serviceaccount:${var.k8s_namespace}:${var.k8s_service_account}"
}

data "aws_iam_policy_document" "irsa_trust" {
  count = var.create_irsa_role ? 1 : 0

  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [var.oidc_provider_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "${var.oidc_provider_url}:sub"
      values   = [local.irsa_sub]
    }

    condition {
      test     = "StringEquals"
      variable = "${var.oidc_provider_url}:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "app" {
  count              = var.create_irsa_role ? 1 : 0
  name               = "spidersilk-app-${var.environment}"
  assume_role_policy = data.aws_iam_policy_document.irsa_trust[0].json
}

data "aws_iam_policy_document" "app" {
  statement {
    sid    = "WriteToCsvBucket"
    effect = "Allow"
    actions = [
      "s3:PutObject",
      "s3:PutObjectAcl",
      "s3:AbortMultipartUpload",
    ]
    resources = ["${aws_s3_bucket.csv_archive.arn}/*"]
  }

  statement {
    sid    = "ListAndReadCsvBucket"
    effect = "Allow"
    actions = [
      "s3:ListBucket",
      "s3:GetBucketLocation",
    ]
    resources = [aws_s3_bucket.csv_archive.arn]
  }

  statement {
    sid    = "ReadCsvObjects"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:GetObjectVersion",
    ]
    resources = ["${aws_s3_bucket.csv_archive.arn}/*"]
  }
}

resource "aws_iam_policy" "app" {
  name   = "spidersilk-app-${var.environment}"
  policy = data.aws_iam_policy_document.app.json
}

resource "aws_iam_role_policy_attachment" "app" {
  count      = var.create_irsa_role ? 1 : 0
  role       = aws_iam_role.app[0].name
  policy_arn = aws_iam_policy.app.arn
}
