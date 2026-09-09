# Hand-off — repoint sms-api-stanford-test onto vivarium-workbench `0.3.0`

> Dropped by the vivarium-workbench session. You already appear to be on
> `deploy/workbench-0.3.0` — this is the full context + guardrails for that work.
> Delete this file when done (it's an untracked scratch note).

We just released **vivarium-workbench `0.3.0`** and need the **sms-api-stanford-test**
overlay repointed onto it.

## What happened upstream (vivarium-workbench repo)
- **PR #453** (merged) — migrated the v2ecoli dashboard *demo* into the workbench
  repo, plus the product-code behind it: pinned-build remote runs, CSRF allowlist +
  reverse-proxy (`--trust-proxy` / `--allowed-origin`) support, `/reports/` +
  study-detail base-path fixes, composite-resolve degradation, and the `pbg-ptools`
  viewer plugin (installed in the combined image) built against decoupled v2ecoli.
- Since then: **#468 / #470** (report charts + interactive embeds now render in the
  v4 study renderer and the PR-attached report), **#469** (snapshot banner wording),
  and **#467** (Alex's pinned-run **progress bar** — Plan 7).
- Version bumped `0.2.0 → 0.3.0`; release **`v0.3.0`** cut → **`ghcr.io/vivarium-collective/vivarium-workbench:0.3.0`**
  is **built & pushed, confirmed live** (linux/amd64).
- **`0.3.0` supersedes `0.2.0` as the deploy target** — it contains everything in
  `0.2.0` plus the report fixes and progress UX, and stays functionally aligned with
  the `7a9620c` demo build stanford-test runs today.

## Task
Repoint the workbench image the **sms-api-stanford-test** overlay deploys onto the
release **`0.3.0`**.

- File: `kustomize/overlays/sms-api-stanford-test/kustomization.yaml`, the `images:`
  entry for `ghcr.io/vivarium-collective/vivarium-workbench`.
- On `main` this is currently `newTag: 0.1.1` (from PR #167); update it to
  **`newTag: 0.3.0`**.
- **Scope: only `sms-api-stanford-test`** — it is the only overlay that deploys the
  workbench (it references `../../base/workbench` directly; the shared base does not,
  and stanford *prod* intentionally does not deploy the workbench yet — it still
  needs its ALB workbench target group + PVC). Do **not** add the workbench to other
  overlays.
- Refresh the pin comment to note `0.3.0` = the demo-migration release + report fixes
  + progress UX (replaces the temporary `build/demo-v2ecoli/7a9620c` SHA).
- Open a standalone PR off `main` for review.

## Watch for
1. **PR #163 (`patch/db-filter`, the simulation-filter feature) currently carries a
   `newTag: 7a9620c` workbench pin on its branch.** If #163 merges as-is it would
   overwrite `main`'s workbench pin back to the dev SHA — a regression. Before/at
   #163's merge, reconcile its workbench pin to **`0.3.0`** (or drop the pin change
   from that PR so it only carries the filter feature). Flag this on #163.
2. **Do NOT delete or garbage-collect the ghcr `build/demo-v2ecoli/7a9620c` image /
   tag** until `0.3.0` is deployed and verified on stanford-test — the live demo pod
   runs it, so removing it early causes `ImagePullBackOff`. It is intentionally
   retained as a record of what was deployed/tested.

## After merging the pin PR
Apply/sync the stanford-test overlay and smoke-test the workbench on `0.3.0`:
- the **PTools Omics Viewer** should render (now served by the `pbg-ptools` plugin,
  not v2ecoli),
- the **pinned-run card** should show the new milestone progress bar,
before calling the demo "on the release."
