# AWS Batch / K8s Backend — Learnings & Gotchas

Captured during initial deployment of the K8s/AWS Batch backend to `sms-api-stanford-test` (April 2026). These are non-obvious issues that cost significant debugging time.

## GovCloud S3 Access from Nextflow

Nextflow's Java AWS SDK does not automatically resolve the correct S3 endpoint in GovCloud (`us-gov-west-1`). Even with `aws.region` set in the Nextflow config profile, S3 calls fail with `Access Denied (Service: S3, Status Code: 403)`.

**Fix:** Inject `aws.client.endpoint = "https://s3.us-gov-west-1.amazonaws.com"` into the Nextflow config's `aws` profile block. Currently done via `sed` on `config.template` before `workflow.py` runs. This is a GovCloud-specific requirement — commercial AWS regions work without it.

## Nextflow `-profile aws` Must Be Explicit

The `aws` profile in `config.template` (which sets `process.executor = 'awsbatch'`, `aws.region`, etc.) is **not active by default**. Nextflow must be invoked with `-profile aws`. Without it, Nextflow uses the `standard` profile and tries to run locally.

The SLURM backend (`simulation_service.py`) passes `-profile {nf_profile_key}` correctly. This was initially missing from the K8s entrypoint.

## `build-and-push-ecr.sh` Requires `USER` Env Var

The script uses `set -eu` and line `IMAGE_TAG="${USER}-image"` runs before argument parsing. In containers where `USER` is unset (e.g., K8s pods running as root), this causes an immediate failure even though `-i` would override the default. Set `USER=sms-api` (or any value) in the container env.

## `workflow.py` Always Calls `build-and-push-ecr.sh -u`

Even when `build_image` is `false` and a full ECR URI is provided as `container_image`, `workflow.py` still calls `build-and-push-ecr.sh -u` to resolve the URI. This means:
- The container running `workflow.py` must have `aws` CLI installed
- AWS credentials must be available (IRSA or instance profile)
- The IRSA role needs `ecr:DescribeRepositories` permission
- Pass `container_image` as short name (`vecoli:5f918eb`), not full URI — workflow.py constructs the full URI itself

## IRSA (IAM Roles for Service Accounts) Setup

For K8s pods to access AWS services (S3, Batch, ECR), the `batch-submit` ServiceAccount needs:
1. **IRSA annotation:** `eks.amazonaws.com/role-arn: arn:aws-us-gov:iam::{account}:role/{role-name}`
2. **Trust policy:** The IAM role must allow `sts:AssumeRoleWithWebIdentity` from the EKS OIDC provider for the specific namespace/service account
3. **Required permissions:** S3 read/write, Batch submit/describe/terminate, ECR describe/pull, CloudWatch logs

The annotation is applied via a kustomize patch in the overlay's `kustomization.yaml`.

## Config Overrides for K8s Backend

When the backend is `k8s` (determined by `get_job_backend()` in `config.py`), the simulation handler (`common/handlers/simulations.py`) overrides HPC-specific config values **before** database insert:
- `emitter_arg` → S3 URI instead of local filesystem path
- `parca_options.outdir` → S3 URI
- `aws` block added (build_image, container_image, region, batch_queue)
- `aws_cdk` and `ccam` keys removed
- `progress_bar` set to `false`

This ensures the database record matches the actual Job config.

## K8s Resource Names Must Be RFC 1123

Experiment IDs with underscores (e.g., `our_first_batch_job`) cause K8s Job/ConfigMap creation to fail. The code sanitizes names: `experiment_id.replace("_", "-").lower()`.

## EKS Node ECR Access

EKS nodes can pull ECR images via the node instance profile — no `imagePullSecrets` needed for ECR. However, `ghcr.io` images require a `ghcr-secret` (sealed secret with dockerconfigjson).

## Sealed Secrets Must Be Re-encrypted Per Cluster

Sealed secrets are encrypted with the cluster's sealed-secrets controller certificate. Secrets from one cluster won't decrypt on another. Run `secrets.sh` to regenerate them for each cluster.

## Docker Build Space on macOS

Building the sms-api Docker image frequently runs out of space in Docker Desktop due to dev dependencies (mypy, ruff, etc.). Two mitigations:
- Use `--no-dev` flag in `uv sync` inside the Dockerfile (`RUN uv sync --frozen --no-install-project --no-dev`)
- Run `docker system prune -a -f` before builds to reclaim space

## `workflow.py` Execution Modes

- `--build-only`: Generates Nextflow files (main.nf, nextflow.config) in `/vEcoli/nextflow_temp/{experiment_id}/` and copies them to the output URI. Returns without running Nextflow.
- Full mode (no flag): Generates files AND runs Nextflow as a subprocess. This is the intended mode for standalone operation (EC2 instances) and the target for the simplified K8s Job.

On EC2, Java and Nextflow are installed on the host. The vEcoli Docker image does NOT include Java/Nextflow. See `docs/plan-single-container-k8s-job.md` for the plan to create a `vecoli-submit` image that adds these.

## Stanford Test Environment

- **EKS cluster region:** `us-gov-west-1`
- **CDK stack prefix:** `smsvpctest`
- **Namespace:** `sms-api-stanford-test`
- **AWS SSO profile:** `stanford-sso`
- **Kubeconfig:** `~/.kube/kubeconfig_stanford_test.yaml`
- **Secrets regeneration:** `kustomize/overlays/sms-api-stanford-test/secrets.sh`
- **Config stack outputs** (looked up by `secrets.sh`): login node instance ID, DB secret ARN, FSx details, Redis endpoint, ALB target groups
