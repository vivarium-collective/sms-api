from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
DEFAULT_SIMULATION_CONFIG = ROOT_DIR / "assets" / "sms_experiment.json"
DEFAULT_BULK_OBSERVABLES = ["--TRANS-ACENAPHTHENE-12-DIOL", "ACETOLACTSYNI-CPLX", "CPD-3729"]
DEFAULT_GENES_OBSERVABLES = ["deoC", "deoD", "fucU"]
DEFAULT_ANALYSIS_OPTIONS = {
    "cpus": 3,
    "multiseed": {
      "ptools_rxns": {
        "n_tp": 8
      },
      "ptools_rna": {
        "n_tp": 8
      },
      "ptools_proteins": {
        "n_tp": 8
      }
    },
    "data_transformation": {
      "ecocyc": {
        "request": [
          {
            "type": "genes",
            "observable_ids": DEFAULT_GENES_OBSERVABLES
          },
          {
            "type": "bulk",
            "observable_ids": DEFAULT_BULK_OBSERVABLES
          }
        ]
      }
    }
  }
