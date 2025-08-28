#!/bin/bash
#SBATCH --job-name=sms-colony-test
#SBATCH --time=30:00
#SBATCH --cpus-per-task 2
#SBATCH --mem=8GB
#SBATCH --partition=vivarium
#SBATCH --qos=vivarium
#SBATCH --output=/home/FCAM/svc_vivarium/prod/htclogs/sms-colony-test.out
#SBATCH --nodelist=mantis-039

set -e
env

config_id="$1"
module load java
module load nextflow
workspace_dir="${HOME}/workspace"
vecoli_dir="${workspace_dir}/vEcoli"
latest_hash=079c43c
cd $vecoli_dir
binds="-B /home/FCAM/svc_vivarium/workspace/vEcoli:/vEcoli"
binds+=" -B /home/FCAM/svc_vivarium/workspace/test_out:/out"
cp $(which nextflow) /tmp/nextflow
chmod +x /tmp/nextflow
binds+=" -B /tmp/nextflow:/usr/bin/nextflow"
binds+=" -B $JAVA_HOME:$JAVA_HOME"
image="/home/FCAM/svc_vivarium/prod/images/vecoli-$latest_hash.sif"  
vecoli_image_root=/vEcoli
image_python_interpreter=/home/FCAM/svc_vivarium/workspace/vEcoli/.venv/bin/python

singularity run $binds $image uv run \
    --env-file $vecoli_image_root/.env \
    python $vecoli_image_root/runscripts/workflow.py \
    --config $vecoli_image_root/configs/$config_id.json