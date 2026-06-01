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
# 0.7.9 — ecoli-sources support (--sources flag), remove vecoli dep, dep bumps
# 0.8.0 — harden ecoli-sources sync (org allowlist, path traversal, size limits, manifest validation)
# 0.8.1 — GUI auto-refresh, remove branch allowlist, mount GUI notebook, improve error messages
# 0.8.2 — fix analysis output metadata (partition parsing), all-domain filtering, restore num_seeds
# 0.9.0 — compose (process-bigraph) subsystem, Python 3.13, /compose/v1/ endpoints
# 0.9.1 — fix test_run_analysis to use HPC-available simulator (203ab2a), graceful GitHub cred skip
# 0.9.4 — fix broken 0.9.3 compose router import (PbgConfigParam/PbgPortSchema missing from models.py);
#          add Phase 3b scaffold, CVE deps bump (Mako/python-multipart/urllib3), analyses reliability
#          (poll_status hang fix, CANCELLED migration, SLURM node pinning removed, silent SSH failure fix),
#          qualification_test.sh fix, PTOOLS_VERIFICATION docs + CI workflow
# 0.9.5 — process-bigraph-native compose subsystem.
#          ARCHITECTURE (todo:56):
#            - Dropped pbest==0.5.5 dependency (was hard-pinning process-bigraph==1.0.5)
#            - Bumped to process-bigraph[server-rest]>=1.4.12,<2 (pulls fastapi-utils, uvicorn, fire, typing-inspect)
#            - New sms_api/compose/containerization.py (in-tree singularity .def renderer, replaces pbest's)
#            - Container %runscript now invokes `python -m process_bigraph.run` (upstream entrypoint)
#            - Upstream process_bigraph.server.rest.make_router(core) mounted at /compose/v1/ (10 routes)
#            - New sms_api/compose/bundle_utils.py wraps process_bigraph.bundle.save_bundle/load_bundle
#              for large composite docs (numpy arrays externalized to Parquet)
#            - DB persistence layer (ProcessRegistryDatabaseService + ORM) KEPT — fundamental to sms-api
#              production-grade architecture; layered on top of upstream's in-memory state
#          PACKAGE REGISTRY (todo:57):
#            - GET /compose/v1/processes and /steps now read live core.link_registry via
#              introspect_core() helper (with ?source=core|db|union query param)
#            - POST /compose/v1/packages (discriminated union: repo_url|local_path|outline),
#              GET /packages, GET /packages/{id}, POST /packages/audit endpoints
#            - sms_api/compose/package_audit.py (in-tree, mirrored from pbg-superpowers — NOT a dep)
#            - atlantis compose packages / package-get / package-audit / package-register CLI
#          UPSTREAM-PARITY CLI (todo:56 Phase 12):
#            - atlantis compose list-processes / list-types / import-types / type-packages
#              mirror upstream router paths
__version__ = "0.9.5"
