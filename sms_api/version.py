# NEWEST(FIRST NEXTFLOW): "0.2.11-dev"
# STABLE: "0.2.10-dev"
# PREVIOUS STABLE: "0.2.8"
# LATEST STABLE (old): "0.2.74-dev"
# LATEST STABLE (most recent before hackathon 1): "0.4.8" -> 0.5.9
# LATEST STABLE AFTER HACKATHON FOR AWS: 0.6.0
# 0.6.2 — task-8 parallel S3 downloads + results-cache emptyDir volume
# 0.6.3 — remove PCS/SLURM/FSx from stanford-test, backend guards on legacy endpoints
# 0.7.0 — Atlantis CLI, AWS Batch backend, PCS/SLURM/FSx removal, ComputeBackend enum
# 0.7.1 — fix public_mode default, stale secret ARN, enforce run_parca on Batch
# 0.7.2 — config template fallback for public vEcoli repo, kustomize tag sync, RKE DB migration
# 0.7.3 — generation range and seed filtering for ptools analysis endpoint
# 0.7.4 — top-level DuckDB filters, strip private analyses from embedded template,
#          repo-aware analysis_options defaults (cd1_* only for private vEcoli repo)
# 0.7.5 — S3 streaming download (fix 504), README image, CLI trailing help, docs update
# 0.7.6 — TUI/GUI feature parity, reactive simulator selection, repo dropdown, list sorting
# 0.7.7 — fix analysis filters (generation_range/lineage_seed inside analysis_options),
#          allow arbitrary public vEcoli branches, bump pytest for CVE fix
# 0.7.8 — explicit config validation (no silent fallback), diagnose_sim.py diagnostic tool
__version__ = "0.7.8"
