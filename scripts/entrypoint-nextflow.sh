#!/bin/bash
# Entrypoint for the Nextflow submit container (K8s Job main container).
#
# Expects:
#   - Nextflow files in /work/nextflow/ (written by init container)
#   - EXPERIMENT_ID env var
#   - NXF_WORK env var (S3 work directory)
#
# Optional:
#   - EVENTS_FILE env var — if set, starts weblog receiver for event capture

set -e

EXPERIMENT_ID="${EXPERIMENT_ID:?EXPERIMENT_ID is required}"
NXF_WORK="${NXF_WORK:?NXF_WORK is required}"
NEXTFLOW_DIR="/work/nextflow"

# Verify init container generated the files
if [ ! -f "$NEXTFLOW_DIR/main.nf" ]; then
    echo "ERROR: main.nf not found in $NEXTFLOW_DIR"
    echo "The init container may not have run successfully."
    ls -la "$NEXTFLOW_DIR/" 2>/dev/null || echo "Directory does not exist"
    exit 1
fi

echo "=== Nextflow workflow files ==="
ls -la "$NEXTFLOW_DIR/"

# Fix include paths — init container generates absolute container paths
# that reference /vEcoli/runscripts/nextflow/; replace with relative paths
sed -i "s|from '/vEcoli/runscripts/nextflow/sim'|from './sim'|g" "$NEXTFLOW_DIR/main.nf"
sed -i "s|from '/vEcoli/runscripts/nextflow/analysis'|from './analysis'|g" "$NEXTFLOW_DIR/main.nf"

echo "=== Starting Nextflow ==="
echo "  Experiment: $EXPERIMENT_ID"
echo "  Work dir:   $NXF_WORK"
echo "  Config:     $NEXTFLOW_DIR/nextflow.config"

# Optional: start weblog receiver for Nextflow event capture
WEBLOG_FLAG=""
if [ -n "$EVENTS_FILE" ]; then
    python3 /usr/local/bin/nextflow-weblog-receiver &
    WEBLOG_PID=$!
    sleep 1
    WEBLOG_PORT=$(cat /tmp/weblog_port_$$ 2>/dev/null || echo "9999")
    rm -f /tmp/weblog_port_$$
    echo "  Weblog:     http://localhost:$WEBLOG_PORT -> $EVENTS_FILE"
    WEBLOG_FLAG="-with-weblog http://localhost:$WEBLOG_PORT"
fi

# Run Nextflow
cd "$NEXTFLOW_DIR"
nextflow -C "$NEXTFLOW_DIR/nextflow.config" run "$NEXTFLOW_DIR/main.nf" \
    -work-dir "$NXF_WORK" \
    -with-report "$NEXTFLOW_DIR/${EXPERIMENT_ID}_report.html" \
    $WEBLOG_FLAG

NF_EXIT=$?

# Cleanup weblog receiver
if [ -n "$WEBLOG_PID" ]; then
    kill $WEBLOG_PID 2>/dev/null || true
    wait $WEBLOG_PID 2>/dev/null || true
fi

echo "=== Workflow completed with exit code: $NF_EXIT ==="
exit $NF_EXIT
