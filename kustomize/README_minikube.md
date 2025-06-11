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

## install Temporal

Temporal is a workflow engine that can be installed on Kubernetes. It is an official
Helm chart and docker-compose configuration. We used [kompose](https://kompose.io)
to bootstrap our kubernetes configuration [kustomize/cluster](./kustomize/cluster) from
the [Temporal docker-compose](https://github.com/temporalio/docker-compose) config.

Temporal is then deployed as its own namespace `temporal` and the services are exposed
within the cluster for use by multiple applications. Temporal can isolate workflows from
different applications by using its own **Temporal Namespaces**.

```bash
cd kustomize/cluster
kubectl create namespace temporal
kubectl kustomize overlays/minikube | kubectl apply --namespace temporal -f -
```
