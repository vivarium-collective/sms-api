# Plan: Multi-Arch Build Pipeline — Batch (ARM64) + K8s (AMD64) with Kaniko

## Problem

- AWS Batch tasks need **ARM64** containers (Graviton compute — cheaper, better perf)
- EKS worker nodes are **AMD64** only (GovCloud limitation)
- CodeBuild ARM64 is not available in `us-gov-west-1`
- Current single-arch EC2 build node cannot build both architectures

## Solution

**Build where you run.** Use the target environment's own compute to build its images:

- **AWS Batch Job (ARM64 Graviton)** → builds `vecoli:{commit}` (ARM64 task image)
- **K8s Job (AMD64 EKS)** → builds `vecoli:{commit}-submit` (AMD64 submit image)

Both use **Kaniko** — a container image builder that runs inside containers without needing a Docker daemon or privileged mode.

## Architecture

```
sms-api (submit_build_image_job)
│
├── AWS Batch Job (Graviton/ARM64 compute)
│   └── Kaniko container:
│       - Clones vEcoli repo
│       - Builds vecoli:{commit} from vEcoli Dockerfile
│       - Pushes to ECR (ARM64 native)
│
└── K8s Job (EKS/AMD64 compute)
    └── Kaniko container:
        - Clones vEcoli repo
        - Builds vecoli:{commit}-amd64-base from vEcoli Dockerfile
        - Builds vecoli:{commit}-submit from Dockerfile-vecoli-submit
        - Pushes both to ECR (AMD64 native)
```

Both jobs run in parallel. sms-api polls both for completion.

## What Gets Built

| Image | Architecture | Used By | Built By |
|-------|-------------|---------|----------|
| `vecoli:{commit}` | ARM64 | AWS Batch tasks (Graviton) | Batch Job (Kaniko) |
| `vecoli:{commit}-submit` | AMD64 | K8s Nextflow head Job (EKS) | K8s Job (Kaniko) |

## Why Kaniko

- **No Docker daemon needed** — runs as a regular container, no DinD complexity
- **No privileged mode** — more secure, works in restricted K8s environments
- **Standard tool** — widely used for K8s-native image builds, maintained by Google
- **Direct ECR push** — authenticates to ECR and pushes without Docker CLI
- **Works in both K8s and Batch** — same tool, same approach, both environments

## Implementation

### 1. Kaniko Container Image

Kaniko provides an official image: `gcr.io/kaniko-project/executor:latest`

For GovCloud (may not have access to gcr.io), mirror to ECR:
```bash
# One-time: pull and push Kaniko to your ECR
docker pull gcr.io/kaniko-project/executor:latest
docker tag gcr.io/kaniko-project/executor:latest \
    476270107793.dkr.ecr.us-gov-west-1.amazonaws.com/kaniko:latest
docker push 476270107793.dkr.ecr.us-gov-west-1.amazonaws.com/kaniko:latest
```

### 2. ARM64 Task Image Build (Batch Job)

sms-api submits an AWS Batch job that runs Kaniko:

```python
batch_client.submit_job(
    jobName=f"build-arm64-{commit}",
    jobQueue=settings.batch_job_queue,  # ARM64/Graviton queue
    jobDefinition=settings.kaniko_job_definition,
    containerOverrides={
        "command": [
            "--context", f"git://git@github.com/CovertLabEcoli/vEcoli-private.git#refs/heads/{branch}",
            "--dockerfile", "runscripts/container/Dockerfile",
            "--destination", f"{ecr_registry}/vecoli:{commit}",
            "--build-arg", f"git_hash={commit}",
            "--build-arg", f"git_branch={branch}",
            "--build-arg", f"timestamp={timestamp}",
            "--git", f"branch={branch}",
        ],
        "environment": [
            {"name": "AWS_DEFAULT_REGION", "value": settings.batch_region},
            {"name": "GIT_SSH_KEY", "value": "/kaniko/ssh-key"},
        ],
    },
)
```

Kaniko handles:
- Git clone (supports SSH keys for private repos)
- Docker build (native ARM64 on Graviton)
- ECR push (authenticates via instance role / IRSA)

### 3. AMD64 Submit Image Build (K8s Job)

sms-api creates a K8s Job with two Kaniko init containers + a completion container:

```yaml
# Step 1: Build AMD64 base vEcoli image
initContainers:
  - name: build-base
    image: <ecr>/kaniko:latest
    args:
      - --context=git://git@github.com/.../vEcoli-private.git#refs/heads/{branch}
      - --dockerfile=runscripts/container/Dockerfile
      - --destination=<ecr>/vecoli:{commit}-amd64-base
      - --build-arg=git_hash={commit}
      - --build-arg=git_branch={branch}

# Step 2: Build submit image (base + Java + Nextflow)
  - name: build-submit
    image: <ecr>/kaniko:latest
    args:
      - --context=dir:///workspace
      - --dockerfile=/workspace/Dockerfile-vecoli-submit
      - --destination=<ecr>/vecoli:{commit}-submit
      - --build-arg=BASE_IMAGE=<ecr>/vecoli:{commit}-amd64-base

containers:
  - name: done
    image: busybox
    command: ["echo", "Build complete"]
```

The `Dockerfile-vecoli-submit` is delivered via ConfigMap (already in the sms-api repo).

### 4. sms-api Code Changes

**`sms_api/simulation/simulation_service_k8s.py`:**

Replace `_build_script` + `_submit_build_ssh` + `_run_build` with:

```python
async def _start_builds(self, simulator_version: SimulatorVersion) -> None:
    """Start ARM64 (Batch) and AMD64 (K8s) image builds in parallel."""

    # ARM64 task image via Batch Job
    batch = boto3.client("batch", region_name=settings.batch_region)
    batch.submit_job(...)

    # AMD64 submit image via K8s Job
    self._k8s.create_job(kaniko_job_spec)
```

**Build status polling:**
- Batch job status: `batch.describe_jobs()`
- K8s job status: existing `_k8s.get_job_status()`
- Both must complete → overall build COMPLETED

**`sms_api/config.py`:**

New:
```python
kaniko_image: str = ""  # ECR URI for Kaniko executor image
kaniko_batch_job_definition: str = ""  # Batch job definition for ARM64 builds
```

Remove:
- `build_node_host`, `build_node_user`, `build_node_key_path`
- `ecr_submit_repository` (submit image uses same `vecoli` repo with `-submit` suffix)

### 5. CDK Changes (sms-cdk repo)

- **Batch Job Definition** for Kaniko ARM64 builds:
  - Container image: `<ecr>/kaniko:latest`
  - Uses Graviton compute environment
  - IAM role with ECR push permissions
  - Mount GitHub SSH key from Secrets Manager

- **ECR Repository** for Kaniko image (one-time mirror from gcr.io)

- **Secrets Manager** secret for GitHub SSH deploy key (may already exist)

### 6. GitHub Repo Access

Kaniko supports git contexts with SSH keys:
```
--context=git://git@github.com/CovertLabEcoli/vEcoli-private.git#refs/heads/master
```

SSH key mounted as a Kubernetes secret or Batch secret.

For K8s: mount the existing `ssh-secret` (already has deploy key)
For Batch: reference Secrets Manager secret in job definition

### 7. Batch Compute Environment

CDK change: add or switch to ARM64/Graviton compute environment for Batch. The existing AMD64 environment can remain for backward compatibility during migration.

## What Stays the Same

- `submit_build_image_job()` public interface (returns JobId)
- Build status polling from CLI/TUI
- K8s simulation Job spec (uses `vecoli:{commit}-submit`)
- Workflow config format (`container_image: vecoli:{commit}`)
- ECR repository name `vecoli`
- `Dockerfile-vecoli-submit` in sms-api repo

## What Gets Removed

- `SSHTarget.BUILD` and build node SSH configuration
- `_build_script()`, `_submit_build_ssh()`, `_run_build()` methods
- `buildshell` from Dockerfile-api
- Build node EC2 instance (after migration verified)
- Build node entries from shared.env

## Migration Path

1. Mirror Kaniko image to ECR
2. Deploy CDK: Batch job definition for Kaniko, Graviton compute environment
3. Update sms-api: replace SSH build with Batch + K8s Kaniko jobs
4. Test: verify both images build and push correctly
5. Switch Batch simulation compute to Graviton
6. Verify EUTE pipeline end-to-end
7. Decommission build node EC2 instance

## Verification

1. Batch Kaniko job completes → `vecoli:{commit}` (ARM64) in ECR
2. K8s Kaniko job completes → `vecoli:{commit}-submit` (AMD64) in ECR
3. K8s simulation Job pulls `vecoli:{commit}-submit` on AMD64 EKS
4. Batch simulation tasks pull `vecoli:{commit}` on ARM64 Graviton
5. `uv run atlantis simulator latest ...` triggers both builds
6. `uv run atlantis simulation run ...` completes successfully
