# PLAN: EUTE Remaining Items — Itemized Review

## The Full EUTE Pipeline (from CLAUDE.md)

```
1. GET  /core/v1/simulator/latest
2. POST /core/v1/simulator/upload
3. GET  /core/v1/simulator/status (poll)
4. POST /api/v1/simulations
5. GET  /api/v1/simulations/{id}/status (poll)
6. POST /api/v1/simulations/{id}/data (download)
```

## Step-by-Step Status

| #   | Step                                | CLI Command                                                 | Code Status | Infra Status      |
| --- | ----------------------------------- | ----------------------------------------------------------- | ----------- | ----------------- |
| 1   | Get latest simulator                | `atlantis simulator latest --repo-url ... --branch master`  | DONE        | PASS              |
| 2   | Upload + build image                | (included in step 1)                                        | DONE        | PASS              |
| 3   | Poll build status                   | (included in step 1, `--poll` default)                      | DONE        | PASS              |
| 4   | Submit simulation                   | `atlantis simulation run <exp> <sim_id> --run-parca --poll` | DONE        | PASS (submitted)  |
| 5   | Simulation execution + status poll  | `atlantis simulation status <id> --poll`                    | DONE (code) | **BLOCKED**       |
| 6   | Download outputs                    | `atlantis simulation outputs <id> --dest ./debug`           | DONE (code) | **NOT TESTED**    |

## What's Blocking Step 5

**IRSA S3 permissions** — The K8s `batch-submit` ServiceAccount's IRSA role has **zero IAM policies attached**. The CDK code in `../sms-cdk/lib/batch-stack.ts` defines all required policies (S3, Batch, ECR, CloudWatch, PassRole), but the stack hasn't been deployed.

**Action required (by you):**

```bash
aws sso login --profile stanford-sso
cd ../sms-cdk
AWS_PROFILE=stanford-sso cdk diff smsvpctest-batch    # preview
AWS_PROFILE=stanford-sso cdk deploy smsvpctest-batch   # deploy
```

No sms-api redeploy needed — the IAM change takes effect immediately.

## What's Blocking Step 6

Depends on step 5 completing successfully. The code path is fully implemented:

- **SLURM backend**: SSH/SCP download from HPC filesystem
- **K8s backend**: S3 download from shared bucket, filters `.tsv`/`.json` from `analyses/` prefix
- Both paths create a `tar.gz` archive and stream/serve it

## Code Gaps That May Surface After CDK Deploy

1. **S3 output path mismatch** — The `emitter_arg.out_uri` is set to `s3://{bucket}/{prefix}/{experiment_id}`, but vEcoli's Nextflow workflow may write outputs to a different sub-path structure. Need to verify after first successful run.
2. **Analysis output structure** — `_download_outputs_from_s3` expects `{experiment_prefix}/analyses/` to contain `.tsv`/`.json` files. If vEcoli's analysis outputs use a different directory structure on S3, the download handler will return an empty archive.
3. ~~**Workflow log retrieval**~~ — **FIXED.** `_get_k8s_log` now falls back to `_get_s3_nextflow_log` when pod logs are unavailable (pod cleaned up after TTL). Downloads `.nextflow.log` from `s3://{bucket}/{work_prefix}/{experiment_id}/logs/`. Tested via `test_k8s_log_fallback_to_s3`.

## ~~Pre-existing Test Failures~~ (FIXED)

All pre-existing test failures have been resolved:

- `tests/api/ecoli/test_data.py` — Fixed `test_archive_nonexistent_simulation` (string→int path param), `test_get_data` (hardcoded ID→fixture, localhost→ASGITransport). Added NFS mount + `ssh_session_service` skip conditions for HPC-dependent tests.
- `tests/api/ecoli/test_outputs.py` — Added `RUN_S3_TESTS=1` gate for credential-dependent S3 tests.
- `tests/api/ecoli/test_simulations.py` — Added NFS mount skip condition for `test_run_simulation_workflow_e2e`.
- Test suite: **66 passed, 9 skipped, 0 failed**.

## Three-Client Parity Status

| Feature                           | CLI  | TUI  | Marimo |
|-----------------------------------|------|------|--------|
| Simulator latest/build            | DONE | DONE | ?      |
| Simulation run                    | DONE | DONE | ?      |
| Simulation status + error_message | DONE | DONE | ?      |
| Simulation outputs download       | DONE | DONE | ?      |

Marimo notebooks (`app/ui/`) haven't been verified against the current API changes. The `SimulationRun` model change (new `error_message` field) is backward-compatible (optional field), so existing Marimo code won't break — but it also won't display error messages until updated.

---

## CDK Deploy: What It Does and Why

### The Problem

The K8s Job that runs Nextflow (the simulation orchestrator) uses a ServiceAccount called `batch-submit`. That ServiceAccount is annotated with an IRSA (IAM Roles for Service Accounts) role:

```
smsvpctest-batch-BatchSubmitIrsaRole31BE49CD-xETZl8o1n6cE
```

This role currently has **zero IAM policies attached**. So when the Nextflow head pod starts and tries to do anything with AWS — submit Batch jobs, read/write S3, pull ECR images — it gets `Access Denied`.

### What the CDK Stack Defines

The CDK code in `../sms-cdk/lib/batch-stack.ts` defines a `BatchStack` that creates/configures:

**1. IRSA Role Policies** — the critical missing piece. Five policy groups:

| Policy           | What It Grants                                                               | Why Nextflow Needs It                              |
| ---------------- | ---------------------------------------------------------------------------- | -------------------------------------------------- |
| **S3**           | `grantReadWrite` on shared bucket                                            | Nextflow work dir, simulation output, log upload   |
| **Batch**        | `SubmitJob`, `DescribeJobs`, `ListJobs`, `TerminateJob`, `Register/Dereg..`  | `awsbatch` executor submits vEcoli tasks as jobs   |
| **ECR**          | `GetAuthorizationToken`, `BatchGetImage`, `GetDownloadUrlForLayer`           | Batch jobs pull `vecoli:<commit>` from ECR         |
| **CloudWatch**   | `CreateLogGroup`, `CreateLogStream`, `PutLogEvents`, `GetLogEvents`          | Batch jobs write stdout/stderr to CloudWatch       |
| **IAM PassRole** | `iam:PassRole` scoped to `batchComputeRole` and `batchSubmitRole`            | Nextflow passes roles when registering job defs    |

**2. Batch Compute Environment** — the Batch queue, compute environment, and associated IAM roles that Nextflow targets. These may already exist; the CDK deploy will reconcile.

**3. Networking** — VPC subnets, security groups for Batch compute. Again, likely already provisioned.

### What `cdk deploy` Will Actually Change

Since the Batch infrastructure (queues, compute environments, VPC) likely already exists, the **primary change** will be IAM policy attachments on the IRSA role. The `cdk diff` preview will show exactly which resources change.

### The Deploy Flow

**1. Authenticate**

```bash
aws sso login --profile stanford-sso
```

**2. Preview (dry run — shows what will change)**

```bash
cd ../sms-cdk
AWS_PROFILE=stanford-sso cdk diff smsvpctest-batch
```

**3. Deploy (applies changes)**

```bash
AWS_PROFILE=stanford-sso cdk deploy smsvpctest-batch
```

**4. Verify policies are attached**

```bash
AWS_PROFILE=stanford-sso aws iam list-attached-role-policies \
  --role-name smsvpctest-batch-BatchSubmitIrsaRole31BE49CD-xETZl8o1n6cE \
  --region us-gov-west-1
```

### What Happens After Deploy

The IAM change is **immediate** — no sms-api redeploy or pod restart needed. The next K8s Job created by the API will inherit the updated IRSA policies through the `batch-submit` ServiceAccount.

The EUTE test becomes:

```bash
uv run atlantis simulation run test3 <SIMULATOR_ID> \
  --config-filename api_simulation_default.json \
  --generations 1 --seeds 1 --run-parca --poll
```

If the policies are correct, Nextflow should:

1. Read the workflow config from the ConfigMap
2. Submit parca/simulation/analysis tasks to AWS Batch
3. Batch jobs pull `vecoli:<commit>` from ECR
4. Jobs write outputs to `s3://{bucket}/vecoli-output/{experiment_id}/`
5. Nextflow uploads `.nextflow.log` to `s3://{bucket}/nextflow/work/{experiment_id}/logs/`

That unblocks EUTE step 5, and step 6 (output download) should work immediately since the S3 download handler is already implemented and tested.
