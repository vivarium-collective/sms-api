terraform {
  required_version = ">= 1.5.7"
  required_providers {
    aws               = { source = "hashicorp/aws", version = "~> 5.50" }
    aws-parallelcluster = {
      source  = "aws-tf/aws-parallelcluster"
      version = "~> 1.1"          # matches ParallelCluster ≥ 3.11
    }
  }
}

provider "aws" {
  region = var.region
}

# ---------- ParallelCluster API ----------
module "pcluster_api" {
  source  = "aws-tf/parallelcluster/aws"
  version = "~> 1.1"
  deploy_parallelcluster_api = true
  api_stage_name             = "prod"
  allowed_vpc_id             = data.terraform_remote_state.network.outputs.vpc_id
}

# ---------- Cluster ----------
resource "aws_parallelcluster_cluster" "slurm" {
  name          = "hpc-slurm-${terraform.workspace}"
  configuration = file("${path.module}/cluster-config.yaml")
  wait_on_create = true          # block until bootstrap complete
  region        = var.region
  # Optional: tags, roles, etc.
}
