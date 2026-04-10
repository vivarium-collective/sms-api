Typical Run Times
=================

These are approximate durations for each stage of the simulation pipeline.
Actual times vary based on cluster load, network speed, and simulation
complexity.

.. list-table::
   :header-rows: 1

   * - Pipeline Stage
     - Approximate Duration
   * - Simulator build (fresh)
     - 5--10 minutes
   * - Simulator build (cached / same commit)
     - seconds
   * - Parca (parameter calculator)
     - 5--8 minutes
   * - Simulation (1 generation, 1 seed)
     - 5--7 minutes
   * - Analysis (8 analysis types)
     - 3--5 minutes
   * - Output download
     - 1--3 minutes (depends on file size and network)
   * - **Full pipeline** (build + parca + sim + analysis)
     - **~20--30 minutes**

Tips:

- Skip parca by omitting ``--run-parca`` if a parca dataset already exists
  for your simulator. This saves ~5--8 minutes.
- Increase ``--seeds`` to run multiple independent lineages in parallel.
  Run time scales sub-linearly since seeds are parallelized on the cluster.
- The simulator build is cached by commit hash. Rebuilding the same commit
  without ``--force`` returns instantly.
