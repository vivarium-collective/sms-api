# Deploying to stanford-test

Step-by-step deployment guide for the `sms-api-stanford-test` environment on EKS in AWS GovCloud.

## Prerequisites

- AWS SSO login: `aws sso login --profile stanford-sso`
- Kubeconfig: `~/.kube/kubeconfig_stanford_test.yaml`
- Docker Desktop running (for container builds)

## Environment Variables

All deploy commands use:
```bash
export AWS_PROFILE=stanford-sso
export KUBECONFIG=~/.kube/kubeconfig_stanford_test.yaml
```

## Deployment Steps

### 1. Bump Version

Update version in both files:
- `pyproject.toml` — `version = "X.Y.Z"`
- `sms_api/version.py` — `__version__ = "X.Y.Z"`

### 2. Build and Push Container Images

```bash
# May need to free Docker space first
docker system prune -a -f

# Build api, ptools, nextflow images and push to ghcr.io
bash kustomize/scripts/build_and_push.sh
```

### 3. Update Image Tags in Kustomization

Edit `kustomize/overlays/sms-api-stanford-test/kustomization.yaml`:
```yaml
images:
  - name: ghcr.io/vivarium-collective/sms-api
    newTag: "X.Y.Z"
  - name: ghcr.io/vivarium-collective/sms-ptools
    newTag: "X.Y.Z"
```

### 4. Regenerate Secrets (if infrastructure changed)

```bash
bash kustomize/overlays/sms-api-stanford-test/secrets.sh
```

This regenerates sealed secrets, SSH known hosts, FSx PV config, Redis endpoints, and ALB target group bindings from CloudFormation stack outputs. Requires `secrets.dat` file (not committed, create from `secrets.dat.template`).

### 5. Apply and Restart

```bash
kubectl apply -k kustomize/overlays/sms-api-stanford-test
kubectl rollout restart deployment api ptools -n sms-api-stanford-test
```

### 6. Verify

```bash
kubectl get pods -n sms-api-stanford-test
# Both api and ptools should be Running 1/1
```

## Database Migration

```bash
# Update migration overlay
# Edit kustomize/overlays/sms-api-stanford-test-db-migration/kustomization.yaml
# Set namespace to sms-api-stanford-test, image tag, and config path

kubectl apply -k kustomize/overlays/sms-api-stanford-test-db-migration
kubectl get jobs -n sms-api-stanford-test
kubectl logs job/alembic-migrate -n sms-api-stanford-test
```

If the database already has the schema (tables exist), stamp instead:
```bash
kubectl exec -it deployment/api -n sms-api-stanford-test -- alembic stamp head
```

## Troubleshooting

### Pods in ImagePullBackOff
Sealed secrets may not have been decrypted yet. Check:
```bash
kubectl get secret ghcr-secret -n sms-api-stanford-test
```
If missing, regenerate with `secrets.sh` and reapply.

### DB Connection Timeout
Check that the RDS security group allows inbound on port 5432 from the EKS node security group.

### Nextflow Job Failures
Check init container and main container logs separately:
```bash
kubectl logs <pod-name> -c generate-workflow -n sms-api-stanford-test  # init
kubectl logs <pod-name> -c nextflow -n sms-api-stanford-test           # main
```

Upload of `.nextflow.log` to S3 happens on job completion (success or failure):
```bash
aws s3 ls s3://{S3_WORK_BUCKET}/nextflow/work/{experiment_id}/logs/
```

### Cleaning Up Failed Jobs
```bash
kubectl delete jobs -n sms-api-stanford-test -l app=sms-api
```
