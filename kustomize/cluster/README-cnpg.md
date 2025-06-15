# Installation of the CNPG Operator

see https://cloudnative-pg.io/documentation/1.26/installation_upgrade/

### download the CNPG Operator

```bash
wget https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/release-1.26/releases/cnpg-1.26.0.yaml
```

### apply the CNPG Operator

```bash
kubectl apply --server-side -f cnpg-1.26.0.yaml
```

### output was

```aiignore
namespace/cnpg-system serverside-applied
customresourcedefinition.apiextensions.k8s.io/backups.postgresql.cnpg.io serverside-applied
customresourcedefinition.apiextensions.k8s.io/clusterimagecatalogs.postgresql.cnpg.io serverside-applied
customresourcedefinition.apiextensions.k8s.io/clusters.postgresql.cnpg.io serverside-applied
customresourcedefinition.apiextensions.k8s.io/databases.postgresql.cnpg.io serverside-applied
customresourcedefinition.apiextensions.k8s.io/imagecatalogs.postgresql.cnpg.io serverside-applied
customresourcedefinition.apiextensions.k8s.io/poolers.postgresql.cnpg.io serverside-applied
customresourcedefinition.apiextensions.k8s.io/publications.postgresql.cnpg.io serverside-applied
customresourcedefinition.apiextensions.k8s.io/scheduledbackups.postgresql.cnpg.io serverside-applied
customresourcedefinition.apiextensions.k8s.io/subscriptions.postgresql.cnpg.io serverside-applied
serviceaccount/cnpg-manager serverside-applied
clusterrole.rbac.authorization.k8s.io/cnpg-database-editor-role serverside-applied
clusterrole.rbac.authorization.k8s.io/cnpg-database-viewer-role serverside-applied
clusterrole.rbac.authorization.k8s.io/cnpg-manager serverside-applied
clusterrole.rbac.authorization.k8s.io/cnpg-publication-editor-role serverside-applied
clusterrole.rbac.authorization.k8s.io/cnpg-publication-viewer-role serverside-applied
clusterrole.rbac.authorization.k8s.io/cnpg-subscription-editor-role serverside-applied
clusterrole.rbac.authorization.k8s.io/cnpg-subscription-viewer-role serverside-applied
clusterrolebinding.rbac.authorization.k8s.io/cnpg-manager-rolebinding serverside-applied
configmap/cnpg-default-monitoring serverside-applied
service/cnpg-webhook-service serverside-applied
deployment.apps/cnpg-controller-manager serverside-applied
mutatingwebhookconfiguration.admissionregistration.k8s.io/cnpg-mutating-webhook-configuration serverside-applied
validatingwebhookconfiguration.admissionregistration.k8s.io/cnpg-validating-webhook-configuration serverside-applied
```

### to check the installation

```bash
kubectl rollout status deployment -n cnpg-system cnpg-controller-manager
```

### output was

```aiignore
deployment "cnpg-controller-manager" successfully rolled out
```

### install the cnpg kubectl plugin

```bash
brew install kubectl-cnpg
```

# install a PostgreSQL cluster

see https://cloudnative-pg.io/documentation/1.26/quickstart/

### create a PostgreSQL cluster

```bash
kubectl create namespace postgres-cluster
kubectl apply -f postgres-cluster/minikube/sms-postgres-cluster.yaml
kubectl get pods -n postgres-cluster
```

### monitor the cluster

```bash
kubectl apply -f postgres-cluster/minikube/pod-monitor.yaml
```
