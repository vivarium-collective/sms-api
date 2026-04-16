/**
 * Quick value comparison: baseline vs single-gen-5 vs seed-1-only
 * to see if any filter actually changes ptools_rna output values.
 */

const BASE_URL = "https://sms.cam.uchc.edu";
const ENDPOINT = `${BASE_URL}/api/v1/analyses`;
const TIMEOUT_MS = 30 * 60 * 1000;

async function post(label, body) {
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
    const data = await r.json();
    console.log(`[${label}] HTTP ${r.status} (${elapsed}s)`);
    return data;
  } catch (e) {
    console.error(`[${label}] ${e.message}`);
    return null;
  } finally {
    clearTimeout(timer);
  }
}

function getValues(data, gene) {
  if (!data || !Array.isArray(data) || !data[0]?.content) return null;
  const lines = data[0].content.split("\n");
  const row = lines.find(l => l.startsWith(gene + "\t"));
  return row ? row.split("\t").slice(1) : null;
}

async function main() {
  const genes = ["EG10001", "EG10017", "EG10100", "EG10500", "EG11000"];

  // seed 1 only — different from the already-cached seed 0
  const seedOne = await post("Seed 1 only", {
    experiment_id: "sim3-test-5062",
    seeds: [1],
    multiseed: [{ name: "ptools_rna", n_tp: 8, variant: 0 }]
  });

  // baseline (cached)
  const baseline = await post("Baseline", {
    experiment_id: "sim3-test-5062",
    multiseed: [{ name: "ptools_rna", n_tp: 8, variant: 0 }]
  });

  console.log("\nVALUE COMPARISON (baseline vs seed-1-only):");
  for (const g of genes) {
    const bv = getValues(baseline, g);
    const sv = getValues(seedOne, g);
    if (!bv || !sv) { console.log(`  ${g}: missing data`); continue; }
    const same = bv.every((v, i) => v === sv[i]);
    console.log(`  ${g}: ${same ? "IDENTICAL" : "DIFFERENT"}`);
    if (!same) {
      console.log(`    baseline: ${bv.join(", ")}`);
      console.log(`    seed 1:   ${sv.join(", ")}`);
    }
  }
}

main().catch(console.error);
