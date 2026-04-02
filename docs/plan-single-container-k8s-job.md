# Plan: Simplify K8s Job to Single Container

## Context

The current K8s Job uses two containers: an init container (vEcoli ECR image) that runs `workflow.py --build-only` to generate Nextflow files, and a main container (sms-nextflow ghcr.io image) that runs Nextflow. This has been fragile — file copying between containers, path fixups via sed, GovCloud endpoint injection, dual image pull secrets, etc.

Per the vEcoli AWS docs (`vEcoli/doc/aws.rst`), the standalone EC2 approach simply runs `python runscripts/workflow.py --config your_config.json` which generates Nextflow files and runs Nextflow in one step. We should replicate this in K8s.

## Approach

**Two-stage Docker build:** Create a `vecoli-submit` image that extends the vEcoli ECR image with Java + Nextflow. Push to ECR alongside the base image. The K8s Job uses this single image — no init container, no runtime installs, no file copying between containers.

## Current Architecture (two containers)

```
K8s Job Pod
├── Init Container (vecoli:{commit} from ECR)
│   ├── Runs: workflow.py --build-only
│   ├── Generates: main.nf, nextflow.config, sim.nf, analysis.nf
│   ├── Copies files to shared emptyDir volume
│   ├── Injects GovCloud S3 endpoint via sed
│   └── Uploads generated files to S3
│
└── Main Container (sms-nextflow:0.5.1 from ghcr.io)
    ├── Verifies init container output
    ├── Fixes include paths via sed
    ├── Runs: nextflow -profile aws -C nextflow.config run main.nf
    └── Uploads logs to S3
```

**Problems with this approach:**
- File copying between containers via emptyDir volume
- Path fixups (sed) for include statements
- GovCloud S3 endpoint injection via sed into generated config
- Two different images from two different registries (ECR + ghcr.io)
- Two sets of image pull secrets
- Missing `-profile aws` flag (caught during testing)
- `USER` env var required for `build-and-push-ecr.sh`
- Fragile coupling between init and main container

## Proposed Architecture (single container)

```
K8s Job Pod
└── Single Container (vecoli-submit:{commit} from ECR)
    ├── Has: Python, aws CLI, Java, Nextflow (all pre-installed)
    ├── Injects GovCloud S3 endpoint into config.template
    ├── Runs: workflow.py --config /config/workflow.json
    │   (generates Nextflow files AND runs Nextflow in one step)
    └── Uploads .nextflow.log to S3 on completion
```

## Changes Required

### 1. New Dockerfile: `Dockerfile-vecoli-submit`

Two-stage build extending the vEcoli ECR image:

```dockerfile
ARG BASE_IMAGE
FROM ${BASE_IMAGE}

# Install Java (required by Nextflow, Debian bookworm default is OpenJDK 17)
RUN apt-get update && apt-get install -y --no-install-recommends default-jre-headless \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Nextflow
ARG NEXTFLOW_VERSION=25.10.2
RUN curl -fsSL "https://github.com/nextflow-io/nextflow/releases/download/v${NEXTFLOW_VERSION}/nextflow" \
    -o /usr/local/bin/nextflow && chmod +x /usr/local/bin/nextflow

WORKDIR /vEcoli
```

- `BASE_IMAGE` build arg: full ECR URI of the base vEcoli image (e.g. `476270107793.dkr.ecr.us-gov-west-1.amazonaws.com/vecoli:5f918eb`)
- Push as `vecoli-submit:{commit}` to a separate ECR repository
- Both images share base layers — submit image adds ~200MB for Java + Nextflow

### 2. Update build script: `_build_script()` in `simulation_service_k8s.py`

After building and pushing the base vEcoli image via `build-and-push-ecr.sh`, build the submit image:

```bash
# ... existing: clone repo + build-and-push-ecr.sh pushes vecoli:{commit} ...

# Build vecoli-submit image with Java + Nextflow on top of base
docker build -t $ECR_REGISTRY/vecoli-submit:$COMMIT \
    --build-arg BASE_IMAGE=$ECR_URI \
    -f Dockerfile-vecoli-submit .
docker push $ECR_REGISTRY/vecoli-submit:$COMMIT
```

The `Dockerfile-vecoli-submit` needs to be available on the build node. Options:
- Embed it in the build script as a heredoc
- Upload it to the build node as part of the SSH command
- Store it in the vEcoli repo (requires upstream change)

### 3. Replace Job spec: `submit_ecoli_simulation_job()` in `simulation_service_k8s.py`

**Container command:**
```bash
# Inject GovCloud S3 endpoint into config.template before workflow.py reads it
sed -i "/region = params.aws_region/a\            client { endpoint = \"https://s3.{region}.amazonaws.com\" }" \
    runscripts/nextflow/config.template

# Run workflow.py in full mode (generates files + runs Nextflow)
python runscripts/workflow.py --config /config/workflow.json

# Capture exit code, upload logs, propagate exit code
; NF_EXIT=$?
; aws s3 cp .nextflow.log s3://{bucket}/{prefix}/{experiment_id}/logs/.nextflow.log || true
; exit $NF_EXIT
```

**Simplified pod spec:**
- Single container using `vecoli-submit:{commit}` from ECR
- No init container
- No `nextflow-files` emptyDir volume
- No `image_pull_secrets` for `ghcr-secret` (ECR auth via node instance profile)
- No `NXF_WORK` or `EXPERIMENT_ID` env vars (workflow.py reads from config JSON)
- Keep: `batch-submit` service account (IRSA), ConfigMap volume at `/config`, `AWS_DEFAULT_REGION`, `USER` env vars

### 4. Config cleanup

- `sms_api/config.py` — Remove `nextflow_container_image` and `ecr_account_id` settings
- `kustomize/config/sms-api-stanford-test/shared.env` — Remove `NEXTFLOW_CONTAINER_IMAGE` and `ECR_ACCOUNT_ID`
- Add `ecr_submit_repository: str = "vecoli-submit"` setting (or similar)

### 5. Remove dead files

- `scripts/entrypoint-nextflow.sh` — K8s Nextflow entrypoint (replaced by inline command)
- `Dockerfile-nextflow` — Separate Nextflow container (replaced by vecoli-submit)
- `scripts/nextflow-weblog-receiver.py` — Only used in Dockerfile-nextflow
- Update `kustomize/scripts/build_and_push.sh` — Remove nextflow image build

### 6. Update tests

- `tests/simulation/test_k8s_backend.py` — Update to reflect single-container Job spec

## Build Pipeline

```
Build Node (ARM64 EC2)
│
├── 1. Clone vEcoli repo
├── 2. build-and-push-ecr.sh → pushes vecoli:{commit} to ECR
└── 3. docker build → pushes vecoli-submit:{commit} to ECR
         (FROM vecoli:{commit}, adds Java + Nextflow)
```

## What Stays the Same

- Handler config overrides in `simulations.py` (emitter_arg, aws block, parca outdir)
- ConfigMap delivery of workflow config JSON
- `_build_script()` / `_submit_build_ssh()` for Docker image builds
- Database schema, API routes
- Base vEcoli image build process

## Verification

1. `uv run pytest tests/simulation/test_k8s_backend.py -v` — unit tests pass
2. `make check` — lint and type check
3. Build base image on build node, then build submit image on top
4. Deploy to stanford-test, submit simulation via API
5. Verify single-container Job runs `workflow.py` end-to-end
6. Check S3 for `.nextflow.log` on failure
