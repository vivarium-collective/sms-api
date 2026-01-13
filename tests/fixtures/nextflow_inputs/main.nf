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
    echo "Mock metadata.json" > metadata.json
    cp $kb/simData.cPickle baseline.cPickle
    """
}

// TODO: do we want to make a ccamHqWorker?
process hqWorker {
    cpus { num_sims }

    memory {
        if ( task.exitStatus in [137, 140] ) {
            task.cpus * 4.GB + 4.GB * (task.attempt - 1)
        } else {
            task.cpus * 4.GB
        }
    }
    time 24.h
    maxRetries 10

    tag "hq_${params.experimentId}_${task.index}"

    executor 'slurm'
    queue 'owners,normal'
    // Run on newer, faster CPUs
    clusterOptions '--prefer="CPU_GEN:GEN|CPU_GEN:SPR" --constraint="CPU_GEN:RME|CPU_GEN:MLN|CPU_GEN:BGM|CPU_GEN:SIE|CPU_GEN:GEN|CPU_GEN:SPR"'
    container null

    input:
    val num_sims

    script:
    server_dir = "${params.publishDir}/${params.experimentId}/nextflow/.hq-server"
    """
    # Start HyperQueue worker with specified options
    hq worker start --manager slurm \\
        --server-dir ${server_dir} \\
        --cpus ${task.cpus} \\
        --resource "mem=sum(${task.cpus * 4096})" \\
        --idle-timeout 5m &

    worker_pid=\$!
    wait \$worker_pid
    exit_code=\$?

    # Only exit with 0 if the exit code is 0 or 1
    # This allows code 1 to be treated as success but propagates all other errors
    if [ \$exit_code -eq 0 ] || [ \$exit_code -eq 1 ]; then
        exit 0
    else
        # Forward the original error code to Nextflow
        exit \$exit_code
    fi
    """

    stub:
    """
    echo "Started HyperQueue worker for $num_sims" \\
        >> $server_dir/worker.log
    """
}

include { simGen0 as sim_gen_1 } from '/projects/SMS/sms_api/dev/repos/53526a7/vEcoli/runscripts/nextflow/sim'
include { sim as sim_gen_2 } from '/projects/SMS/sms_api/dev/repos/53526a7/vEcoli/runscripts/nextflow/sim'
include { sim as sim_gen_3 } from '/projects/SMS/sms_api/dev/repos/53526a7/vEcoli/runscripts/nextflow/sim'
include { sim as sim_gen_4 } from '/projects/SMS/sms_api/dev/repos/53526a7/vEcoli/runscripts/nextflow/sim'
include { sim as sim_gen_5 } from '/projects/SMS/sms_api/dev/repos/53526a7/vEcoli/runscripts/nextflow/sim'
include { analysisMultiSeed } from '/projects/SMS/sms_api/dev/repos/53526a7/vEcoli/runscripts/nextflow/analysis'
include { analysisMultiGeneration } from '/projects/SMS/sms_api/dev/repos/53526a7/vEcoli/runscripts/nextflow/analysis'
include { analysisSingle } from '/projects/SMS/sms_api/dev/repos/53526a7/vEcoli/runscripts/nextflow/analysis'

workflow {
	runParca(params.config)
	runParca.out.toList().set {kb}
    createVariants(params.config, kb)
        .variantSimData
        .flatten()
        .set { variantCh }
    createVariants.out
        .variantMetadata
        .set { variantMetadataCh }
	channel.of( 0..<35 ).set { seedCh }
	sim_gen_1(params.config, variantCh.combine(seedCh).combine([1]), '0')
	sim_gen_1.out.nextGen0.set { sim_gen_1_nextGen }
	sim_gen_2(sim_gen_1_nextGen)
	sim_gen_2.out.nextGen0.set { sim_gen_2_nextGen }
	sim_gen_3(sim_gen_2_nextGen)
	sim_gen_3.out.nextGen0.set { sim_gen_3_nextGen }
	sim_gen_4(sim_gen_3_nextGen)
	sim_gen_4.out.nextGen0.set { sim_gen_4_nextGen }
	sim_gen_5(sim_gen_4_nextGen)
	sim_gen_5.out.nextGen0.set { sim_gen_5_nextGen }
	sim_gen_1.out.metadata.mix(sim_gen_2.out.metadata, sim_gen_3.out.metadata, sim_gen_4.out.metadata, sim_gen_5.out.metadata).set { simCh }

    simCh
        .groupTuple(by: [1, 2], size: 175, remainder: true)
        .map { tuple(it[0][0], it[1], it[2]) }
        .set { multiSeedCh }

	analysisMultiSeed(params.config, kb, multiSeedCh, variantMetadataCh)

    simCh
        .groupTuple(by: [1, 2, 3], size: 5, remainder: true)
        .map { tuple(it[0][0], it[1], it[2], it[3]) }
        .set { multiGenerationCh }

	analysisMultiGeneration(params.config, kb, multiGenerationCh, variantMetadataCh)
	analysisSingle(params.config, kb, simCh, variantMetadataCh)
    // Start a HyperQueue worker for every 4 concurrent sims
    if ( params.hyperqueue ) {
        variantCh.combine( seedCh )
            .buffer( size: 4, remainder: true )
            .map { it.size() }
            .set { hqChannel }
        hqWorker( hqChannel )
    }
}
