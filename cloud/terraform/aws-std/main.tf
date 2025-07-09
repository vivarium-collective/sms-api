#######################################################################
# Globals
#######################################################################
locals {
  name   = "blueprint-demo"          # change if you wish
  region = "us-west-2"               # or read from a var/env
  tags   = { Blueprint = local.name }
}

provider "aws" {
  region = local.region
}

#######################################################################
# VPC — 1 public + 2 private subnets per AZ
#######################################################################
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.1"                 # latest 5.x at publish time :contentReference[oaicite:1]{index=1}

  name = "${local.name}-vpc"
  cidr = "10.0.0.0/16"

  azs             = slice(data.aws_availability_zones.available.names, 0, 3)
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

  enable_nat_gateway = true
  tags               = local.tags
}

data "aws_availability_zones" "available" {
  filter {
    name   = "opt-in-status"
    values = ["opt-in-not-required"]
  }
}

#######################################################################
# EKS control-plane + one managed node group
#######################################################################
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.31"               # current major :contentReference[oaicite:2]{index=2}

  cluster_name    = local.name
  cluster_version = "1.31"           # EKS latest as of July 2025
  subnet_ids      = module.vpc.private_subnets
  vpc_id          = module.vpc.vpc_id

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

#######################################################################
# Core add-ons — using Blueprints Addons module (v5 pattern)
#######################################################################
module "addons" {
  source  = "aws-ia/eks-blueprints-addons/aws"
  version = "~> 1.21"                # July 2025 latest :contentReference[oaicite:3]{index=3}

  cluster_name               = module.eks.cluster_name
  cluster_endpoint           = module.eks.cluster_endpoint
  cluster_version            = module.eks.cluster_version
  oidc_provider_arn          = module.eks.oidc_provider_arn
  cluster_security_group_id  = module.eks.cluster_primary_security_group_id
  vpc_id                     = module.vpc.vpc_id

  # enable/override specific add-ons
  addons = {
    # AWS-managed
    vpc-cni    = { most_recent = true }
    kube-proxy = { most_recent = true }
    coredns    = { most_recent = true }

    # storage
    aws-ebs-csi-driver = { most_recent = true }
  }
}

#######################################################################
# One Team (IAM → Kubernetes RBAC)
#######################################################################
module "dev_team" {
  source  = "aws-ia/eks-blueprints-teams/aws"
  version = "~> 1.0"

  name       = "dev-team"
  users      = ["arn:aws:iam::111122223333:user/alice"]
  namespaces = ["dev"]

  depends_on = [module.addons]        # ensures cluster is ready
}
