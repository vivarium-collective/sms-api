### to run
```bash
terraform init
terraform apply
# copy the command printed in outputs, then:
$(terraform output -raw kubeconfig_command)
kubectl get nodes
```
