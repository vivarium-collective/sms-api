# PLAN: Deploy CDK BatchStack to fix IRSA S3 permissions

## Problem

The EUTE workflow reaches step 4 (simulation submission) successfully, but the Nextflow K8s Job fails with:

```
Access Denied (Service: S3, Status Code: 403)
```

The IRSA role `smsvpctest-batch-BatchSubmitIrsaRole31BE49CD-xETZl8o1n6cE` used by the `batch-submit` K8s ServiceAccount has **zero policies attached** — no S3, no Batch, no ECR, nothing.

The CDK code in `../sms-cdk/lib/batch-stack.ts` correctly defines all required policies (S3, Batch, ECR, CloudWatch, PassRole), but the stack hasn't been deployed with the IRSA config yet.

## Fix

Deploy the CDK BatchStack from `../sms-cdk`:

```bash
cd ../sms-cdk
AWS_PROFILE=stanford-sso cdk deploy smsvpctest-batch
```

This will attach the following policies to the IRSA role:
- **S3**: `grantReadWrite` on `smsvpctest-shared-sharedbucket60d199d6-abfvwv0day91` (Nextflow work dir, simulation output)
- **Batch**: `SubmitJob`, `DescribeJobs`, `ListJobs`, `TerminateJob`, `RegisterJobDefinition`, `DeregisterJobDefinition`, `DescribeJobDefinitions`
- **ECR**: `GetAuthorizationToken`, `BatchGetImage`, `GetDownloadUrlForLayer`, `BatchCheckLayerAvailability`, `DescribeRepositories`
- **CloudWatch Logs**: `CreateLogGroup`, `CreateLogStream`, `PutLogEvents`, `GetLogEvents`, `DescribeLogGroups`
- **IAM PassRole**: for Batch job definitions (scoped to `batchComputeRole` and `batchSubmitRole`)

## Prerequisites

1. AWS SSO auth: `aws sso login --profile stanford-sso`
2. CDK bootstrapped in the account (should already be done)
3. Node.js + CDK CLI installed: `npm install -g aws-cdk`

## Steps

```bash
# 1. Auth
aws sso login --profile stanford-sso

# 2. Go to CDK repo
cd ../sms-cdk

# 3. Install deps (if needed)
npm install

# 4. Verify what will change (dry run)
AWS_PROFILE=stanford-sso cdk diff smsvpctest-batch

# 5. Deploy
AWS_PROFILE=stanford-sso cdk deploy smsvpctest-batch

# 6. Verify the role now has policies
AWS_PROFILE=stanford-sso aws iam list-role-policies \
  --role-name smsvpctest-batch-BatchSubmitIrsaRole31BE49CD-xETZl8o1n6cE \
  --region us-gov-west-1

# 7. Back to sms-api — re-test the EUTE
cd ../sms-api

# No redeploy of sms-api needed — the IAM change is immediate.
# Just submit a new simulation:
uv run atlantis simulation run test3 11 \
  --config-filename api_simulation_default.json \
  --generations 1 --seeds 1 --run-parca --poll
```

## Verification

After CDK deploy, the simulation should progress past the S3 access error. Monitor with:

```bash
# K8s Job status
KUBECONFIG=~/.kube/kube_stanford_test.yml \
  kubectl logs job/nf-sim11-test3-XXXX -n sms-api-stanford-test -f

# Or via CLI
uv run atlantis simulation status <SIM_ID>
```

Expected Nextflow output should show processes starting:
```
N E X T F L O W  ~  version 25.10.2
[runParca] process > ...
[runSimulation] process > ...
[runAnalysis] process > ...
```

## Current EUTE State (as of 2026-04-03)

| Step | Command | Status |
|------|---------|--------|
| 1. Get latest simulator | `atlantis simulator latest --repo-url ... --branch master` | PASS |
| 2. Upload + build | (included in step 1) | PASS |
| 3. Poll build status | (included in step 1) | PASS |
| 4. Submit simulation | `atlantis simulation run test2 11 --run-parca` | PASS (submitted) |
| 5. Simulation execution | K8s Job → Nextflow → AWS Batch | BLOCKED (S3 403) |
| 6. Download outputs | `atlantis simulation outputs <ID> --dest ./debug` | NOT YET |

## Notes

- The `api` deployment does NOT use the `batch-submit` ServiceAccount — it uses the default SA. The IRSA role only affects the Nextflow K8s Jobs created by the API.
- The simulation status polling (`atlantis simulation status 28`) also returns errors — this may be a separate issue with the status endpoint not handling K8s Job status correctly, or it could be because the job failed immediately.
- The `--run-parca` flag is required for K8s/Batch workflows because `sim_data_path` defaults to a SLURM-specific FSx path that doesn't exist in K8s containers.
