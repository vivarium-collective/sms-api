#!/usr/bin/env bash

SIMULATOR_HASH="$1"


add_json_key() {
  local json_path="$1"
  local key="$2"
  local value="$3"

  if [[ ! -f "$json_path" ]]; then
    echo "Error: file not found: $json_path" >&2
    return 1
  fi

  # value must be valid JSON
  jq --arg key "$key" \
     --argjson value "$value" \
     '. + {($key): $value}' \
     "$json_path" > "${json_path}.tmp" \
  && mv "${json_path}.tmp" "$json_path"
}


submit_simulation() {
  repo_dir="/projects/SMS/sms_api/dev/repos/${SIMULATOR_HASH}/vEcoli"
  config_path="${repo_dir}/configs/sms_ccam.json"
  container_image="/projects/SMS/sms_api/dev/images/vecoli-${SIMULATOR_HASH}.sif"
  add_json_key "$config_path" ccam \
    "{\"build_image\": false, \"wait\": false, \"container_image\": \"$container_image\"}"
  rm -rf /projects/SMS/sms_api/dev/sims/sms_ccam \
    && uv run --no-cache --env-file /projects/SMS/sms_api/dev/.hpc_env runscripts/workflow.py --config configs/sms_ccam.json --build-only
}

submit_simulation "$SIMULATOR_HASH"

