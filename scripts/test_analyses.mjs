/**
 * Verify all PTOOLS.md examples against POST /api/v1/analyses on RKE.
 *
 * sim3-test-5062: 3 seeds (0,1,2), 10 generations (0-9)
 *
 * NOTE: The generation/seed filter fix (placing them inside analysis_options)
 * requires deployment of v0.7.7+. Until then, filtered and unfiltered results
 * will be identical because vEcoli doesn't see the filters.
 */

const BASE_URL = "https://sms.cam.uchc.edu";
const ENDPOINT = `${BASE_URL}/api/v1/analyses`;
const TIMEOUT_MS = 30 * 60 * 1000;

function parseTsv(content) {
  if (!content) return { header: [], rows: {} };
  const lines = content.split("\n").filter(Boolean);
  const header = lines[0].split("\t");
  const rows = {};
  for (let i = 1; i < lines.length; i++) {
    const cells = lines[i].split("\t");
    rows[cells[0]] = cells.slice(1);
  }
  return { header, rows };
}

async function postAnalysis(label, body) {
  console.log(`\n${"=".repeat(70)}`);
  console.log(`[${label}]`);
  console.log(`Body: ${JSON.stringify(body)}`);

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  const start = Date.now();

  try {
    const response = await fetch(ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });

    const elapsed = ((Date.now() - start) / 1000).toFixed(1);
    const text = await response.text();
    let data;
    try { data = JSON.parse(text); } catch { data = null; }

    if (!response.ok) {
      console.error(`  FAIL — HTTP ${response.status} (${elapsed}s)`);
      console.error(data ? JSON.stringify(data, null, 2) : text.slice(0, 2000));
      return { ok: false, status: response.status, elapsed, label };
    }

    console.log(`  HTTP ${response.status} (${elapsed}s)`);
    let tsv = null;
    if (Array.isArray(data) && data.length > 0) {
      tsv = parseTsv(data[0].content);
      const rowCount = Object.keys(tsv.rows).length;
      console.log(`  ${data[0].filename}: ${rowCount} genes, ${tsv.header.length} cols`);
      // Show first 3 genes
      const sample = Object.entries(tsv.rows).slice(0, 3);
      for (const [gene, vals] of sample) {
        console.log(`    ${gene}: ${vals.join(", ")}`);
      }
    }

    return { ok: true, status: response.status, elapsed, label, data, tsv };
  } catch (err) {
    const elapsed = ((Date.now() - start) / 1000).toFixed(1);
    console.error(`  ${err.name === "AbortError" ? "TIMEOUT" : "ERROR"} (${elapsed}s): ${err.message}`);
    return { ok: false, error: err.message, elapsed, label };
  } finally {
    clearTimeout(timer);
  }
}

async function main() {
  const results = [];

  // PTOOLS.md Example 1: Generation range (gen 2-5)
  results.push(await postAnalysis("Gen range 2-5", {
    experiment_id: "sim3-test-5062",
    generation_start: 2,
    generation_end: 5,
    multiseed: [{ name: "ptools_rna", n_tp: 8, variant: 0 }]
  }));

  // PTOOLS.md Example 2: Skip first N (gen 3+)
  results.push(await postAnalysis("Skip first 3 gens (gen 3+)", {
    experiment_id: "sim3-test-5062",
    generation_start: 3,
    multiseed: [{ name: "ptools_rna", n_tp: 8, variant: 0 }]
  }));

  // PTOOLS.md Example 3: Single generation (gen 5 only)
  results.push(await postAnalysis("Single gen (gen 5)", {
    experiment_id: "sim3-test-5062",
    generation_start: 5,
    generation_end: 5,
    multiseed: [{ name: "ptools_rna", n_tp: 8, variant: 0 }]
  }));

  // PTOOLS.md Example 4: Seed filter (seed 0 only)
  results.push(await postAnalysis("Seed 0 only", {
    experiment_id: "sim3-test-5062",
    seeds: [0],
    multiseed: [{ name: "ptools_rna", n_tp: 8, variant: 0 }]
  }));

  // PTOOLS.md Example 5: Combined (gen 3+, seeds 0 & 2)
  results.push(await postAnalysis("Gen 3+, seeds 0 & 2", {
    experiment_id: "sim3-test-5062",
    generation_start: 3,
    seeds: [0, 2],
    multiseed: [{ name: "ptools_rna", n_tp: 8, variant: 0 }]
  }));

  // PTOOLS.md Example 6: No filters (backwards compat)
  results.push(await postAnalysis("No filters (backwards compat)", {
    experiment_id: "sim3-test-5062",
    multiseed: [{ name: "ptools_rna", n_tp: 8, variant: 0 }]
  }));

  // Summary
  console.log(`\n${"=".repeat(70)}`);
  console.log("SUMMARY");
  console.log("=".repeat(70));
  for (const r of results) {
    const genes = r.tsv ? Object.keys(r.tsv.rows).length : "?";
    const cols = r.tsv ? r.tsv.header.length : "?";
    console.log(`  ${r.ok ? "PASS" : "FAIL"}  ${r.label}  (${r.elapsed}s, ${genes} genes, ${cols} cols)`);
  }

  const allPass = results.every(r => r.ok);
  console.log(`\n  ${allPass ? "All requests returned HTTP 200." : "Some requests failed."}`);
  console.log("  NOTE: Filter values will only differ from baseline after v0.7.7+ is deployed.");
}

main().catch(console.error);
