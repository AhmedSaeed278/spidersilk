variable "region" {
  description = "AWS region for the S3 bucket and IAM resources."
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)."
  type        = string
  default     = "dev"
}

variable "bucket_name" {
  description = "S3 bucket name. Must be globally unique. Leave empty to derive from environment + account ID."
  type        = string
  default     = ""
}

variable "glacier_transition_days" {
  description = "Days after which non-current and current versions transition to GLACIER."
  type        = number
  default     = 30
}

variable "expire_days" {
  description = "Days after which objects expire (and become eligible for deletion)."
  type        = number
  default     = 365
}

variable "noncurrent_expire_days" {
  description = "Days after which noncurrent versions expire."
  type        = number
  default     = 90
}

variable "oidc_provider_arn" {
  description = "ARN of the cluster's OIDC provider (used for IRSA). Required if create_irsa_role = true."
  type        = string
  default     = ""
}

variable "oidc_provider_url" {
  description = "URL of the OIDC provider (no https://), e.g. oidc.spidersilk.k8s.local"
  type        = string
  default     = ""
}

variable "create_irsa_role" {
  description = "Whether to create the IRSA role that grants the app S3 access. Set to false if running against LocalStack or before the cluster exists."
  type        = bool
  default     = true
}

variable "k8s_namespace" {
  description = "Kubernetes namespace running the Spidersilk app."
  type        = string
  default     = "spidersilk"
}

variable "k8s_service_account" {
  description = "Kubernetes service account name running the app."
  type        = string
  default     = "spidersilk"
}
