#!/usr/bin/env nextflow

/*
 * SMS CCAM real simulation workflow for integration testing.
 * This version uses the actual vEcoli simulation modules and produces parquet output.
 * It runs a minimal simulation (1 seed, 1 generation) for testing purposes.
 */

nextflow.enable.dsl=2

// Import simulation processes from vEcoli
include { simGen0 as sim_gen_1 } from '/projects/SMS/sms_api/dev/repos/53526a7/vEcoli/runscripts/nextflow/sim'

// Import analysis processes from vEcoli
// NOTE: analysisSingle disabled due to vEcoli bug (make_sim_data_dict undefined)
// include { analysisSingle } from '/projects/SMS/sms_api/dev/repos/53526a7/vEcoli/runscripts/nextflow/analysis'

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
    # Use pre-installed venv directly to avoid editable install issues
    export PYTHONPATH="${params.projectRoot}:\$PYTHONPATH"
    ${params.projectRoot}/.venv/bin/python ${params.projectRoot}/runscripts/parca.py --config "$config" -o "\$(pwd)"
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
    # Use pre-installed venv directly to avoid editable install issues
    export PYTHONPATH="${params.projectRoot}:\$PYTHONPATH"
    ${params.projectRoot}/.venv/bin/python ${params.projectRoot}/runscripts/create_variants.py \
        --config "$config" --kb "$kb" -o "\$(pwd)"
    """

    stub:
    """
    cp $kb/simData.cPickle variant_1.cPickle
    echo "Mock variant 1" >> variant_1.cPickle
    echo '{"variants": ["variant_1"]}' > metadata.json
    cp $kb/simData.cPickle baseline.cPickle
    """
}

workflow {
    // Use pre-existing parca dataset (skip running parca for speed)
    // The sim_data_path in config points to existing parca output
    kb_dir = file(params.sim_data_path).getParent()
    Channel.fromPath(kb_dir).toList().set { kb }

    // Create variants from config
    createVariants(params.config, kb)
        .variantSimData
        .flatten()
        .set { variantCh }
    createVariants.out
        .variantMetadata
        .set { variantMetadataCh }

    // Single seed for integration test
    channel.of(params.lineage_seed).set { seedCh }

    // Run first generation simulation
    sim_gen_1(params.config, variantCh.combine(seedCh).combine([1]), '0')
    sim_gen_1.out.metadata.set { simCh }

    // Run single cell analysis on simulation output
    // NOTE: analysisSingle disabled due to vEcoli bug (make_sim_data_dict undefined)
    // analysisSingle(params.config, kb, simCh, variantMetadataCh)
}
