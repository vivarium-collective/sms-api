/**
 * Run an E. coli analysis (long-running, blocking request).
 * @returns {Promise<any>} Parsed JSON response
 */
async function runEcoliAnalysis() {
  const url = "https://sms.cam.uchc.edu/v1/ecoli/analyses";

  const payload = {
    experiment_id: "sms_multigeneration",
    multigeneration: [
      {
        name: "ptools_rxns",
        n_tp: 18,
        variant: 0
      }
    ],
    multiseed: [
      {
        name: "ptools_rxns",
        n_tp: 3,
        variant: 0
      }
    ]
  };

  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(
      `Analysis failed (${response.status}): ${text}`
    );
  }

  return await response.json();
}

async function main() {
  try {
    console.log("Starting analysis...");
    const result = await runEcoliAnalysis();
    result.forEach((i, ptoolsOutput) => {
        console.log(`${i}: Got ptools output:`);
        console.log(ptoolsOutput);
    })
    console.log("Analysis complete:", result);
  } catch (err) {
    console.error("Analysis error:", err);
  }
}

function mainSync() {
    (async () => {
      try {
        console.log("Starting analysis...");
        const result = await runEcoliAnalysis();
        console.log("Analysis complete:", result);
      } catch (err) {
        console.error("Analysis error:", err);
      }
    })();

}
