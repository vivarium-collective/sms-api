### running the example

```bash
export AWS_PROFILE=my-govcloud-profile
terraform init
terraform apply        # ~15 min
$(terraform output -raw kubeconfig_command)
kubectl get nodes      # should list 3 m6i.large nodes
```
### What’s still on you to decide
* Inbound access – lock the control-plane (cluster_endpoint_public_access = false) once you have a VPN or Direct Connect path.

* Ingress / ALB Controller – if you need it, mirror the aws-load-balancer-controller image into a private ECR repo in GovCloud and point the Helm chart at that. The Blueprints add-on can take a repository override.

* Observability – AMP (Amazon Managed Service for Prometheus) isn’t present, so choose another Prometheus stack (self-hosted, Grafana Cloud, etc.) or mirror its images the same way.

* CI/CD – Blueprints GitOps module works, but you must host your Argo CD images privately or allow outbound internet to the public gallery.


With this baseline you have a TLS-encrypted, KMS-protected EKS cluster that uses only services and images natively available in AWS GovCloud. Feel free to ask for deeper hardening, private API-only mode, IPv6, or additional team/on-call patterns!