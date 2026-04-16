/**
 * Test generation/seed filtering with "single" analysis type instead of "multiseed".
 * vEcoli's multiseed analysis ignores gen/seed filters — single should respect them.
 */

const BASE_URL = "https://sms.cam.uchc.edu";
const ENDPOINT = `${BASE_URL}/api/v1/analyses`;
const TIMEOUT_MS = 30 * 60 * 1000;

function parseTsv(content) {
  if (!content) return null;
  const lines = content.split("\n").filter(Boolean);
  const header = lines[0].split("\t");
  const rows = {};
  for (let i = 1; i < lines.length; i++) {
    const cells = lines[i].split("\t");
    rows[cells[0]] = cells.slice(1);
  }
  return { header, rows, rowCount: Object.keys(rows).length };
}

async function post(label, body) {
  console.log(`\n${"=".repeat(70)}`);
  console.log(`[${label}]`);
  console.log(`Body: ${JSON.stringify(body)}`);

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  const start = Date.now();

  try {
    const r = await fetch(ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    const elapsed = ((Date.now() - start) / 1000).toFixed(1);
    const text = await r.text();
    let data;
    try { data = JSON.parse(text); } catch { data = null; }

    if (!r.ok) {
      console.error(`  FAIL — HTTP ${r.status} (${elapsed}s)`);
      if (data?.detail) {
        const d = data.detail;
        console.error(`  Error: ${d.message || d}`);
        if (d.error_log) console.error(`  Log: ${d.error_log.slice(-500)}`);
      } else {
        console.error(text.slice(0, 500));
      }
      return { ok: false, status: r.status, elapsed, label };
    }

    console.log(`  HTTP ${r.status} (${elapsed}s)`);
    const tsvs = [];
    if (Array.isArray(data)) {
      for (const item of data) {
        const tsv = parseTsv(item.content);
        if (tsv) {
          console.log(`  ${item.filename}: ${tsv.rowCount} rows, ${tsv.header.length} cols`);
          const sample = Object.entries(tsv.rows).slice(0, 2);
          for (const [gene, vals] of sample) {
            console.log(`    ${gene}: ${vals.join(", ")}`);
          }
        }
        tsvs.push({ filename: item.filename, tsv });
      }
    }
    return { ok: true, status: r.status, elapsed, label, data, tsvs };
  } catch (e) {
    const elapsed = ((Date.now() - start) / 1000).toFixed(1);
    console.error(`  ERROR (${elapsed}s): ${e.message}`);
    return { ok: false, error: e.message, elapsed, label };
  } finally {
    clearTimeout(timer);
  }
}

async function main() {
  // Baseline: single ptools_rna, no filters
  const baseline = await post("Single: no filters", {
    experiment_id: "sim3-test-5062",
    single: [{ name: "ptools_rna", n_tp: 8, variant: 0 }]
  });

  // Filtered: single ptools_rna, gen 2-5
  const genFiltered = await post("Single: gen 2-5", {
    experiment_id: "sim3-test-5062",
    generation_start: 2,
    generation_end: 5,
    single: [{ name: "ptools_rna", n_tp: 8, variant: 0 }]
  });

  // Filtered: single ptools_rna, seed 1 only
  const seedFiltered = await post("Single: seed 1 only", {
    experiment_id: "sim3-test-5062",
    seeds: [1],
    single: [{ name: "ptools_rna", n_tp: 8, variant: 0 }]
  });

  // Compare values
  console.log(`\n${"=".repeat(70)}`);
  console.log("VALUE COMPARISON");
  console.log("=".repeat(70));

  const comparisons = [
    ["Gen 2-5 vs baseline", baseline, genFiltered],
    ["Seed 1 vs baseline", baseline, seedFiltered],
  ];

  for (const [label, a, b] of comparisons) {
    if (!a?.tsvs?.[0]?.tsv || !b?.tsvs?.[0]?.tsv) {
      console.log(`  ${label}: SKIP (missing data)`);
      continue;
    }
    const aRows = a.tsvs[0].tsv.rows;
    const bRows = b.tsvs[0].tsv.rows;
    let diffs = 0, same = 0;
    for (const gene of Object.keys(aRows).slice(0, 50)) {
      if (!bRows[gene]) { diffs++; continue; }
      const match = aRows[gene].every((v, i) => v === bRows[gene][i]);
      if (match) same++; else diffs++;
    }
    console.log(`  ${label}: ${diffs} differ, ${same} identical (first 50 genes)`);
    if (diffs > 0) console.log(`    CONFIRMED: filter changes output`);
    else console.log(`    WARNING: output identical despite filter`);
  }
}

main().catch(console.error);
