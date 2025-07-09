###############################################################################
# Import cluster details from stage 2
###############################################################################
data "terraform_remote_state" "eks" {
  backend = "s3"
  config = {
    bucket = "tf-state-123456789012"
    key    = "dev/eks/terraform.tfstate"
    region = "us-west-2"
  }
}

locals {
  cluster_name  = data.terraform_remote_state.eks.outputs.cluster_name
  cluster_tags  = { Environment = "blueprint-dev" }
}

###############################################################################
# Add-ons (Blueprints v5)
###############################################################################
module "addons" {
  source  = "aws-ia/eks-blueprints-addons/aws"
  version = "~> 1.21"

  cluster_name               = local.cluster_name
  cluster_endpoint           = data.terraform_remote_state.eks.outputs.cluster_endpoint
  cluster_version            = "1.31"
  oidc_provider_arn          = data.terraform_remote_state.eks.outputs.oidc_provider
  cluster_security_group_id  = data.terraform_remote_state.eks.outputs.management_security_group_id
  vpc_id                     = data.terraform_remote_state.eks.outputs.vpc_id

  addons = {
    vpc-cni            = { most_recent = true }
    kube-proxy         = { most_recent = true }
    coredns            = { most_recent = true }
    aws-ebs-csi-driver = { most_recent = true }
  }
}

###############################################################################
# Example team
###############################################################################
module "dev_team" {
  source  = "aws-ia/eks-blueprints-teams/aws"
  version = "~> 1.0"

  name       = "dev-team"
  users      = ["arn:aws:iam::111122223333:user/alice"]
  namespaces = ["dev"]

  depends_on = [module.addons]
}
