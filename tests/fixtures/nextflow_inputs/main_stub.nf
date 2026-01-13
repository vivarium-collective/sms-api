#!/usr/bin/env nextflow

/*
 * Self-contained SMS CCAM workflow for integration testing.
 * This version is simplified to run in -stub mode without external dependencies.
 * It tests the core workflow DAG: runParca -> createVariants -> simGen0 -> analysis
 */

nextflow.enable.dsl=2

process runParca {
    // Run ParCa using parca_options from config JSON
    publishDir "${params.publishDir}/${params.experimentId}/parca", mode: "copy"

    label "parca"

    input:
    path config

    output:
    path 'kb'

    script:
    """
    uv run ${params.projectRoot}/runscripts/parca.py --config "$config" -o "\$(pwd)"
    """

    stub:
    """
    mkdir kb
    echo "Mock sim_data" > kb/simData.cPickle
    echo "Mock raw_data" > kb/rawData.cPickle
    echo "Mock raw_validation_data" > kb/rawValidationData.cPickle
    echo "Mock validation_data" > kb/validationData.cPickle
    """
}

process analysisParca {
    publishDir "${params.publishDir}/${params.experimentId}/parca/analysis", mode: "copy"

    label "slurm_submit"

    input:
    path config
    path kb

    output:
    path 'plots/*'

    script:
    """
    uv run ${params.projectRoot}/runscripts/analysis.py --config "$config" \
        --sim_data_path="$kb/simData.cPickle" \
        --validation_data_path="$kb/validationData.cPickle" \
        -o "\$(pwd)/plots" \
        -t parca
    """

    stub:
    """
    mkdir plots
    echo -e "$config\n\n$kb" > plots/test.txt
    """
}

process createVariants {
    // Parse variants in config JSON to generate variants
    publishDir "${params.publishDir}/${params.experimentId}/variant_sim_data", mode: "copy"

    label "slurm_submit"

    input:
    path config
    path kb

    output:
    path '*.cPickle', emit: variantSimData
    path 'metadata.json', emit: variantMetadata

    script:
    """
    uv run ${params.projectRoot}/runscripts/create_variants.py \
        --config "$config" --kb "$kb" -o "\$(pwd)"
    """

    stub:
    """
    cp $kb/simData.cPickle variant_1.cPickle
    echo "Mock variant 1" >> variant_1.cPickle
    cp $kb/simData.cPickle variant_2.cPickle
    echo "Mock variant 2" >> variant_2.cPickle
    echo '{"variants": ["variant_1", "variant_2"]}' > metadata.json
    cp $kb/simData.cPickle baseline.cPickle
    """
}

// Simplified simulation process for stub testing
process runSimulation {
    publishDir "${params.publishDir}/${params.experimentId}/sim", mode: "copy"

    label "slurm_submit"

    input:
    path config
    path variant_data
    val seed

    output:
    path 'sim_out/*', emit: simOutput
    tuple val(seed), path('sim_out'), emit: metadata

    script:
    """
    echo "Running simulation with seed=$seed variant=$variant_data"
    mkdir sim_out
    echo "sim_data_seed_$seed" > sim_out/simOut.cPickle
    """

    stub:
    """
    mkdir sim_out
    echo "stub simulation seed=$seed variant=$variant_data" > sim_out/simOut.cPickle
    echo "daughter_state" > sim_out/daughter.cPickle
    """
}

// Simplified analysis process for stub testing
process runAnalysis {
    publishDir "${params.publishDir}/${params.experimentId}/analysis", mode: "copy"

    label "slurm_submit"

    input:
    path config
    path kb
    tuple val(seed), path(sim_out)
    path variant_metadata

    output:
    path 'analysis_out/*'

    script:
    """
    echo "Running analysis for seed=$seed"
    mkdir analysis_out
    echo "analysis_result_seed_$seed" > analysis_out/result.txt
    """

    stub:
    """
    mkdir analysis_out
    echo "stub analysis seed=$seed" > analysis_out/result.txt
    """
}

workflow {
    // Run Parca to generate knowledge base
    runParca(params.config)
    runParca.out.toList().set { kb }

    // Run Parca analysis
    analysisParca(params.config, kb)

    // Create variants from config
    createVariants(params.config, kb)

    // Use small seed range for stub testing (0, 1 = 2 seeds)
    // channel.of(0, 1).set { seedCh }
    channel.of(0..<22).set { seedCh }  // 22 seeds (0-21)

    // Get variants and run simulations
    createVariants.out.variantSimData
        .flatten()
        .first()
        .set { firstVariant }

    // Run simulations for each seed
    runSimulation(params.config, firstVariant, seedCh)

    // Run analysis on simulation outputs
    runAnalysis(
        params.config,
        kb,
        runSimulation.out.metadata,
        createVariants.out.variantMetadata
    )
}
