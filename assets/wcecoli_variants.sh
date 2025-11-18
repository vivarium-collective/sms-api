## Set C - 3 growth rates from different conditions
# Used for figure 2
DESC="SET C 4 gens 256 seeds 3 conditions with growth noise and D period" \
VARIANT="condition" FIRST_VARIANT_INDEX=0 LAST_VARIANT_INDEX=2 \
SINGLE_DAUGHTERS=1 N_GENS=4 N_INIT_SIMS=256 \
MASS_DISTRIBUTION=1 GROWTH_RATE_NOISE=1 D_PERIOD_DIVISION=1 \
RUN_AGGREGATE_ANALYSIS=0 \
python runscripts/fireworks/fw_queue.py

## Set D - changes to RNAP and ribosome expression
# Used for figure 2
# Misc. options consistent with Set C

DESC="SET D4 4 gens 256 seeds, unfit ribosome and rna poly expression" \
VARIANT="wildtype" FIRST_VARIANT_INDEX=0 LAST_VARIANT_INDEX=0 \
SINGLE_DAUGHTERS=1 N_GENS=4 N_INIT_SIMS=256 \
MASS_DISTRIBUTION=1 GROWTH_RATE_NOISE=1 D_PERIOD_DIVISION=1 \
DISABLE_RIBOSOME_CAPACITY_FITTING=1 DISABLE_RNAPOLY_CAPACITY_FITTING=1 \
RUN_AGGREGATE_ANALYSIS=0 \
python runscripts/fireworks/fw_queue.py
