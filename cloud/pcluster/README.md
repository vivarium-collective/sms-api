### create the cluster - executed from within govcloud

```bash
pcluster create-cluster my-hpc -c cluster_govcloud.yaml
```

Confirm stack creation progress in the GovCloud CloudFormation console.

### to submit jobs
pcluster ssh my-hpc to reach the head node and submit jobs with sbatch.