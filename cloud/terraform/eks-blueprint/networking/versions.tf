terraform {
  required_version = ">= 1.7.0"
  required_providers {
    aws = { source = "hashicorp/aws"  version = "~> 5.0" }
  }
}

variable "region" { default = "us-west-2" }
provider "aws" { region = var.region }
