#######################################################################
# Provider — stay inside the GovCloud partition + FIPS STS
#######################################################################
provider "aws" {
  region                  = var.region      # us-gov-west-1 or us-gov-east-1
  sts_regional_endpoints  = "regional"      # avoid the public/global STS endpoint
  default_tags = {
    Blueprint = var.cluster_name
  }
}

data "aws_availability_zones" "azs" {
  state = "available"
}

#######################################################################
# VPC — simple 3-AZ (private+public) layout
#######################################################################
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${var.cluster_name}-vpc"
  cidr = "10.128.0.0/16"

  azs             = slice(data.aws_availability_zones.azs.names, 0, 3)
  private_subnets = ["10.128.1.0/24", "10.128.2.0/24", "10.128.3.0/24"]
  public_subnets  = ["10.128.101.0/24", "10.128.102.0/24", "10.128.103.0/24"]

  enable_nat_gateway = true
}

#######################################################################
# EKS control-plane + managed nodes (no Fargate in GovCloud)
#######################################################################
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.31"

  cluster_name    = var.cluster_name
  cluster_version = "1.31"            # 1.31 available in GovCloud :contentReference[oaicite:1]{index=1}
  subnet_ids      = module.vpc.private_subnets
  vpc_id          = module.vpc.vpc_id

  enable_irsa     = true

  # Secrets encryption (KMS key auto-created)
  create_kms_key             = true
  cluster_encryption_config   = [{ resources = ["secrets"] }]

  eks_managed_node_groups = {
    default = {
      instance_types = ["m6i.large"]
      desired_size   = 3
      min_size       = 1
      max_size       = 6
    }
  }
}

#######################################################################
# Add-ons — only ones known to exist in GovCloud today
#######################################################################
module "addons" {
  source  = "aws-ia/eks-blueprints-addons/aws"
  version = "~> 1.21"

  cluster_name               = module.eks.cluster_name
  cluster_endpoint           = module.eks.cluster_endpoint
  cluster_version            = module.eks.cluster_version
  oidc_provider_arn          = module.eks.oidc_provider_arn
  cluster_security_group_id  = module.eks.cluster_primary_security_group_id
  vpc_id                     = module.vpc.vpc_id

  addons = {
    vpc-cni             = { most_recent = true }
    kube-proxy          = { most_recent = true }
    coredns             = { most_recent = true }
    aws-ebs-csi-driver  = { most_recent = true }  # storage
  }
}

#######################################################################
# One platform/team example (IAM → K8s RBAC)
#######################################################################
module "dev_team" {
  source  = "aws-ia/eks-blueprints-teams/aws"
  version = "~> 1.0"

  name       = "dev-team"
  users      = ["arn:aws-us-gov:iam::111122223333:user/alice"]
  namespaces = ["dev"]

  depends_on = [module.addons]
}
