# Plan: Multi-Arch Build Pipeline with CodeBuild (No Step Functions)

## Problem

- AWS Batch tasks need **ARM64** containers (Graviton compute — cheaper, better perf)
- EKS worker nodes are **AMD64** only (GovCloud limitation)
- Current build node is a single EC2 instance — builds one architecture only

## Solution

Two independent CodeBuild jobs — one ARM64, one AMD64 — each builds what it needs natively. No Step Functions, no multi-platform manifests, no orchestration layer.

## Architecture

```
sms-api (submit_build_image_job)
│
├── Start CodeBuild (ARM64 compute)
│   └── Clone vEcoli, build + push vecoli:{commit}
│       (ARM64 task image for Batch)
│
└── Start CodeBuild (AMD64 compute)
    └── Clone vEcoli, build + push vecoli:{commit}-submit
        (AMD64 submit image: vEcoli + Java + Nextflow, for EKS K8s Job)
```

Both jobs run independently and in parallel. sms-api polls both for completion.

## What Gets Built

| Image | Architecture | Used By | Built In |
|-------|-------------|---------|----------|
| `vecoli:{commit}` | ARM64 | AWS Batch tasks (Graviton) | CodeBuild ARM64 |
| `vecoli:{commit}-submit` | AMD64 | K8s Nextflow head Job (EKS) | CodeBuild AMD64 |

No multi-platform manifests. Explicit tags, explicit architectures.

## Implementation

### 1. CDK Stack (sms-cdk repo)

Creates:
- **CodeBuild project `vecoli-build-arm64`**
  - Compute: `BUILD_GENERAL1_SMALL`, `ARM_CONTAINER`
  - Image: `aws/codebuild/amazonlinux2-aarch64-standard:2.0`
  - Privileged mode (Docker builds)
- **CodeBuild project `vecoli-build-amd64`**
  - Compute: `BUILD_GENERAL1_SMALL`, `LINUX_CONTAINER`
  - Image: `aws/codebuild/amazonlinux2-x86_64-standard:4.0`
  - Privileged mode (Docker builds)
- **IAM role** for CodeBuild: ECR push/pull, CloudWatch Logs, Secrets Manager read
- **Secrets Manager secret** for GitHub SSH deploy key (clone private vEcoli repo)
- **ECR repository** `vecoli` (if not exists)

Stack outputs:
- `Arm64ProjectName` — CodeBuild ARM64 project name
- `Amd64ProjectName` — CodeBuild AMD64 project name
- `GitSecretArn` — Secrets Manager ARN for GitHub credentials

### 2. sms-api: Replace SSH build with CodeBuild

**New config settings** (`sms_api/config.py`):
```python
codebuild_arm64_project: str = ""  # CodeBuild project name for ARM64 builds
codebuild_amd64_project: str = ""  # CodeBuild project name for AMD64 builds
```

**Remove:**
- `build_node_host`, `build_node_user`, `build_node_key_path`
- `SSHTarget.BUILD` enum value
- `_build_script()`, `_submit_build_ssh()`, `_run_build()` methods
- `buildshell` from Dockerfile-api
- Build node entries from shared.env

**New methods** in `SimulationServiceK8s`:

```python
async def _start_codebuild(self, simulator_version: SimulatorVersion) -> None:
    """Start ARM64 + AMD64 CodeBuild jobs in parallel."""
    codebuild = boto3.client("codebuild", region_name=settings.batch_region)

    # ARM64: build task image (vecoli:{commit})
    codebuild.start_build(
        projectName=settings.codebuild_arm64_project,
        environmentVariablesOverride=[
            {"name": "COMMIT", "value": commit},
            {"name": "BRANCH", "value": branch},
            {"name": "REPO_URL", "value": repo_url},
            {"name": "IMAGE_TAG", "value": commit},
        ],
    )

    # AMD64: build submit image (vecoli:{commit}-submit)
    codebuild.start_build(
        projectName=settings.codebuild_amd64_project,
        environmentVariablesOverride=[
            {"name": "COMMIT", "value": commit},
            {"name": "BRANCH", "value": branch},
            {"name": "REPO_URL", "value": repo_url},
            {"name": "IMAGE_TAG", "value": f"{commit}-submit"},
            {"name": "BUILD_SUBMIT", "value": "true"},
        ],
    )
```

**Build status polling:** `codebuild.batch_get_builds()` returns build status. Both builds must complete for the overall build to be "done". Map to existing `JobStatus`:
- Both `SUCCEEDED` → `COMPLETED`
- Either `FAILED` → `FAILED`
- Either `IN_PROGRESS` → `RUNNING`

### 3. CodeBuild Buildspecs

**ARM64 buildspec** (task image — same as current `build-and-push-ecr.sh`):
```yaml
version: 0.2
env:
  secrets-manager:
    SSH_KEY: "vecoli-github-deploy-key:ssh-private-key"
phases:
  pre_build:
    commands:
      - ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
      - ECR_REGISTRY="${ACCOUNT_ID}.dkr.ecr.${AWS_DEFAULT_REGION}.amazonaws.com"
      - aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_REGISTRY
      - mkdir -p ~/.ssh && echo "$SSH_KEY" > ~/.ssh/id_rsa && chmod 600 ~/.ssh/id_rsa
      - ssh-keyscan github.com >> ~/.ssh/known_hosts 2>/dev/null
      - git clone --depth 1 --branch $BRANCH --single-branch $REPO_URL vEcoli
      - cd vEcoli && git fetch --depth 1 origin $COMMIT && git checkout $COMMIT
  build:
    commands:
      - cd vEcoli
      - bash runscripts/container/build-and-push-ecr.sh
          -i $IMAGE_TAG -r vecoli -R $AWS_DEFAULT_REGION
```

**AMD64 buildspec** (submit image — builds base then layers Java + Nextflow):
```yaml
version: 0.2
env:
  secrets-manager:
    SSH_KEY: "vecoli-github-deploy-key:ssh-private-key"
phases:
  pre_build:
    commands:
      - ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
      - ECR_REGISTRY="${ACCOUNT_ID}.dkr.ecr.${AWS_DEFAULT_REGION}.amazonaws.com"
      - aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_REGISTRY
      - mkdir -p ~/.ssh && echo "$SSH_KEY" > ~/.ssh/id_rsa && chmod 600 ~/.ssh/id_rsa
      - ssh-keyscan github.com >> ~/.ssh/known_hosts 2>/dev/null
      - git clone --depth 1 --branch $BRANCH --single-branch $REPO_URL vEcoli
      - cd vEcoli && git fetch --depth 1 origin $COMMIT && git checkout $COMMIT
  build:
    commands:
      - cd vEcoli
      # Build base AMD64 image first (needed as base for submit)
      - bash runscripts/container/build-and-push-ecr.sh
          -i ${COMMIT}-amd64-base -r vecoli -R $AWS_DEFAULT_REGION
      # Build submit image on top
      - BASE_URI=$(bash runscripts/container/build-and-push-ecr.sh
          -i ${COMMIT}-amd64-base -r vecoli -R $AWS_DEFAULT_REGION -u)
      - |
        cat > /tmp/Dockerfile-submit <<'EOF'
        ARG BASE_IMAGE
        FROM ${BASE_IMAGE}
        USER root
        RUN apt-get update && apt-get install -y --no-install-recommends default-jre-headless \
            && apt-get clean && rm -rf /var/lib/apt/lists/*
        ARG NEXTFLOW_VERSION=25.10.2
        RUN curl -fsSL "https://github.com/nextflow-io/nextflow/releases/download/v${NEXTFLOW_VERSION}/nextflow" \
            -o /usr/local/bin/nextflow && chmod +x /usr/local/bin/nextflow
        WORKDIR /vEcoli
        EOF
      - docker build -t $ECR_REGISTRY/vecoli:$IMAGE_TAG
          --build-arg BASE_IMAGE=$BASE_URI
          -f /tmp/Dockerfile-submit /tmp
      - docker push $ECR_REGISTRY/vecoli:$IMAGE_TAG
```

### 4. K8s Job and Batch Config

No changes needed to the K8s Job spec — it already uses `vecoli:{commit}-submit`.

For Batch, `container_image` in the workflow config is `vecoli:{commit}` which `workflow.py` resolves via `build-and-push-ecr.sh -u`. This returns the ARM64 image URI.

### 5. Batch Compute Environment

CDK change: switch Batch compute environment from AMD64 to ARM64/Graviton instances. The `vecoli:{commit}` image is now ARM64.

## What Stays the Same

- `submit_build_image_job()` public interface
- Build status polling from CLI/TUI (just polls CodeBuild instead of LocalTaskService)
- K8s Job spec (uses `vecoli:{commit}-submit`)
- Workflow config format
- ECR repository name `vecoli`
- `Dockerfile-vecoli-submit` (reference copy in sms-api repo)

## Migration Path

1. Deploy CDK stack with CodeBuild projects + IAM + Secrets Manager
2. Update sms-api: replace SSH build with CodeBuild invocation
3. Test with a new commit (both jobs build successfully)
4. Switch Batch compute to Graviton instances
5. Remove build node EC2 instance, SSH config, `SSHTarget.BUILD`

## Verification

1. Both CodeBuild jobs complete successfully
2. ECR has `vecoli:{commit}` (ARM64) and `vecoli:{commit}-submit` (AMD64)
3. K8s Job pulls `vecoli:{commit}-submit` on AMD64 EKS nodes
4. Batch tasks pull `vecoli:{commit}` on ARM64 Graviton compute
5. Full EUTE pipeline works end-to-end via `atlantis` CLI
