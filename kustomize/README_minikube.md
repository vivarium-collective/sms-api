## Sealed Secrets setup

1. install sealed secrets and the controller

   ```bash
   brew install kubeseal
   helm repo add sealed-secrets https://bitnami-labs.github.io/sealed-secrets
   helm install sealed-secrets -n kube-system \
        --set-string fullnameOverride=sealed-secrets-controller sealed-secrets/sealed-secrets
   ```

2. create a secret and seal it

   ```bash
   kubectl create secret generic secret-name --dry-run=client --from-literal=foo=bar -o yaml | \
       kubeseal \
         --controller-name=sealed-secrets-controller \
         --controller-namespace=kube-system \
         --format yaml > mysealedsecret.yaml

   kubectl apply -f mysealedsecret.yaml
   ```
