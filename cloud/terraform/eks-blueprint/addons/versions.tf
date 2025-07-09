terraform {
  required_version = ">= 1.7.0"
  required_providers {
    aws         = { source = "hashicorp/aws"         version = "~> 5.0" }
    kubernetes  = { source = "hashicorp/kubernetes"  version = "~> 2.25" }
    helm        = { source = "hashicorp/helm"        version = "~> 2.12" }
  }
}

variable "region" { default = "us-west-2" }
provider "aws" { region = var.region }
