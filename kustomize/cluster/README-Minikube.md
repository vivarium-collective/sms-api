# local minikube config

## technologies

| technology                             | description                                                        |
| -------------------------------------- | ------------------------------------------------------------------ |
| Kubespray (on prem cluster)            | FluxCD (GitOps), Sealed Secrets, Certificate Manager               |
| Lens                                   | nice visual tool for Kubernetes clusters                           |
| minikube (local dev cluster)           | kubectl (manual deploy), plain secrets, self-signed certs          |
| Kustomize                              | to organize k8s manifests for multiple environments                |
| FluxCD                                 | for continuous deployment and GitOps                               |
| Sealed Secrets                         | for secret management of encrypted secrets in Git per each cluster |
| Certificate Manager with Let's Encrypt | for automatic refresh of SSL certificates                          |
| Nginx Ingress controller               | for reverse proxies and CORS handling                              |
| Persistent Volumes/Claims              | to map NFS mounts to pods                                          |
| CloudNativePG                          | for PostgreSQL database management                                 |

# local minikube config

#### This should be run in the `kustomize` directory:

```bash
cd kustomize
```

### install Lens

### install and start minikube on macos

```bash
brew install qemu
brew install socket_vmnet
brew tap homebrew/services
# HOMEBREW=$(which brew) && sudo ${HOMEBREW} services start socket_vmnet
# minikube start --driver qemu --network socket_vmnet --memory=8g --cpus=2
# on M
minikube start --memory=32g --cpus=8
minikube addons enable metrics-server

brew install kubectl
brew install helm
```

### install kube-prometheus-stack

see https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

kubectl create namespace monitoring
helm install prometheus --namespace monitoring prometheus-community/kube-prometheus-stack
```

in Lens, you can see the prometheus pods and services in the monitoring namespace.
Log into Grafana with admin and the password from the following command.

```bash
kubectl get secret --namespace monitoring prometheus-grafana -o jsonpath="{.data.admin-password}" | base64 --decode ; echo
```

### install NATS helm repo

```bash
helm repo add nats https://nats-io.github.io/k8s/helm/charts/
helm repo update
helm install nats nats/nats
```

### set up ingress controller

```bash
minikube addons enable ingress
kubectl get pods -n ingress-nginx
# kubectl patch configmap/ingress-nginx-controller -n ingress-nginx --type merge -p '{"data":{"allow-snippet-annotations":"true"}}'
```

### Sealed Secrets setup

install sealed secrets and the controller

```bash
brew install kubeseal
helm repo add sealed-secrets https://bitnami-labs.github.io/sealed-secrets
helm install sealed-secrets -n kube-system \
     --set-string fullnameOverride=sealed-secrets-controller sealed-secrets/sealed-secrets
```

# prom-operator

create a secret and seal it

```bash
kubectl create secret generic secret-name --dry-run=client --from-literal=foo=bar -o yaml | \
    kubeseal \
      --controller-name=sealed-secrets-controller \
      --controller-namespace=kube-system \
      --format yaml > mysealedsecret.yaml

kubectl apply -f mysealedsecret.yaml
```

### Certificate Manager setup

```bash
brew install cmctl
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.16.1/cert-manager.yaml
cmctl check api
```

### Install CloudNativePG (see README-cnpg.md for more details)

```aiignore
kubectl apply --server-side -f cluster/cnpg-operator/cnpg-1.26.0.yaml
```

### Install the PostgreSQL database cluster

```aiignore

```

````bash
# Configure minikube networking for local development

### set up DNS entries for ingress routing

- vcell webapp and all api services are mapped to minikube.local, create local DNS entry for minikube.local

```bash
#echo "$(minikube ip) minikube.local" | sudo tee -a /etc/hosts
echo "127.0.0.1 minikube.local" | sudo tee -a /etc/hosts
```

- **note** on mapping to localhost rather than minikube ip address:
  from https://github.com/kubernetes/minikube/issues/13510. "Hi, I can confirm that running minikube tunnel works for me on m1 with the docker driver.
  Keep in mind that your etc/hosts file needs to map to 127.0.0.1, instead of the output
  of minikube ip or kubectl get ingress - this is an important gotcha."

# deploying sms-api services to minikube

# NOW, RUN GENERATE SECRETS SCRIPT (sms_dev_secrets.sh)

### verify the kustomization scripts

```bash
kubectl create namespace sms-api-local
kubectl kustomize overlays/sms-api-local | kubectl apply --dry-run=client --validate=true -f -
```

### apply the kustomization scripts

```bash
kubectl kustomize overlays/sms-api-local | kubectl apply -f -
```

### create sealed secrets (see [scripts/README.md](scripts/README.md))

# expose services from minikube cluster

### expose ingress routing to localhost as minikube.local and webapp.minikube.local

for vcell-rest, vcell-api and s3proxy services

```bash
sudo minikube tunnel
```

### build and push the containers (!_)

```bash
docker login ghcr.io -u <GITHUB_USERNAME> -p <GITHUB_CONTAINER_ACCESS_TOKEN>
./scripts/build_and_push.sh
```

### expose NATS message broker to UCH routable ip address

for nats service to receive status messages from simulation workers on HPC cluster

```bash
export EXTERNAL_IP=$(ifconfig | grep 155.37 | awk '{print $2}' | cut -d'-' -f1)
export DEV_NAMESPACE=remote
# bypass services of type LoadBalancer or NodePort - directly export deployment ports
sudo kubectl port-forward --address ${EXTERNAL_IP} -n ${DEV_NAMESPACE} deployment/nats 4222:4222
# set jmshost_sim_external to $EXTERNAL_IP in ./config/jimdev/submit.env
sed -i '' "s/jmshost_sim_external=.*/jmshost_sim_external=${EXTERNAL_IP}/" ./config/jimdev/submit.env
```
````

# _Workflow_ - Making a change and reflecting it locally:

1. Make your changes
2. `make new`
3. Go to Lens under Deployments (minikube) and restart the deployment.
4. Go to the pod and select a new random port forward.

### To get the postgres password:

```bash
kubectl get secret sms-postgres-cluster-app -n postgres-cluster -o jsonpath="{.data.password}" | base64 -d
```

### making updates

./scripts/build_and_push.sh
kubectl kustomize overlays/sms-api-local | kubectl apply -f -
