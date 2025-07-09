variable "region" {
  description = "GovCloud region to deploy into"
  type        = string
  default     = "us-gov-west-1"
}

variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
  default     = "govcloud-blueprint"
}
