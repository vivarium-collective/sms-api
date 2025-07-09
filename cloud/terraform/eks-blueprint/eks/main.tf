###############################################################################
# Bring in VPC outputs from stage 1
###############################################################################
data "terraform_remote_state" "vpc" {
  backend = "s3"
  config = {
    bucket = "tf-state-123456789012"
    key    = "dev/networking/terraform.tfstate"
    region = "us-west-2"
  }
}

locals {
  name = "blueprint-dev"
  tags = { Environment = local.name }
}

###############################################################################
# EKS Cluster + one managed node group
###############################################################################
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.31"

  cluster_name    = local.name
  cluster_version = "1.31"

  vpc_id     = data.terraform_remote_state.vpc.outputs.vpc_id
  subnet_ids = data.terraform_remote_state.vpc.outputs.private_subnets

  enable_irsa   = true

  # Secrets-encryption (creates KMS key automatically)
  create_kms_key           = true
  cluster_encryption_config = [{ resources = ["secrets"] }]

  eks_managed_node_groups = {
    default = {
      instance_types = ["m6i.large"]
      desired_size   = 3
      min_size       = 1
      max_size       = 6
    }
  }

  tags = local.tags
}
