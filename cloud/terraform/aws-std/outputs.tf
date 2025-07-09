output "kubeconfig_command" {
  value = "aws eks update-kubeconfig --region ${local.region} --name ${module.eks.cluster_name}"
}
