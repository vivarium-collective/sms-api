-- List simulation jobs
SELECT
      SUBSTRING(sim.git_repo_url || ':' || sim.git_branch || ':' || sim.git_commit_hash FROM 19) AS simulator,
      'id=' || s.id || ' ' || (s.config->>'experiment_id') AS simulation,
      h.slurmjobid as job_id,
      h.status,
      h.start_time,
      DATE_TRUNC('second', COALESCE(h.end_time, NOW()) - h.start_time) AS duration,
      h.error_message
  FROM simulation s
  JOIN simulator sim ON s.simulator_id = sim.id
  LEFT JOIN hpcrun h ON h.jobref_simulation_id = s.id AND h.job_type = 'SIMULATION'
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
