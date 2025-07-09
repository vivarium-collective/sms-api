output "cluster_name"   { value = module.eks.cluster_name }
output "cluster_arn"    { value = module.eks.cluster_arn }
output "oidc_provider"  { value = module.eks.oidc_provider_arn }
output "kubeconfig_cmd" {
  value = "aws eks update-kubeconfig --region ${var.region} --name ${module.eks.cluster_name}"
}
