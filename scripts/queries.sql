-- List simulation jobs
SELECT
      'id=' || s.id AS simulation,
      SUBSTRING(sim.git_repo_url || ':' || sim.git_branch || ':' || sim.git_commit_hash FROM 19) AS simulator,
      s.config_filename,
      s.experiment_id,
      h.slurmjobid as job_id,
      h.start_time,
      -- DATE_TRUNC('second', COALESCE(h.end_time, NOW()) - h.start_time) AS duration,
      TO_CHAR(COALESCE(h.end_time, NOW()) - h.start_time, 'HH24:MI:SS') AS duration,
      h.status
--       , h.error_message
  FROM simulation s
  JOIN simulator sim ON s.simulator_id = sim.id
  LEFT JOIN hpcrun h ON h.jobref_simulation_id = s.id AND h.job_type = 'SIMULATION'
--   where h.status = 'RUNNING'
  where (sim.git_commit_hash = '7b11ba7' or sim.git_commit_hash = '700044e' or sim.git_commit_hash = '9285cee' or sim.git_commit_hash = '321804d' or sim.git_commit_hash = '6768e44' or sim.git_commit_hash = '7d61649')
  ORDER BY s.created_at DESC;

-- List simulations with truncated config
SELECT
    s.id as sim_id,
    s.created_at,
    s.simulator_id as simulator,
    s.parca_dataset_id as parca_id,
    LEFT(s.config::text, 100) AS config
FROM simulation s
ORDER BY s.created_at DESC;
