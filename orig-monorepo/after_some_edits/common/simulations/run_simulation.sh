#!/usr/bin/env bash

config_path=$1
test_path=/Users/alexanderpatrie/desktop/repos/ecoli/composites/ecoli_configs/test_installation.json

if [ "$config_path" == "" ]; then
  config_path="$test_path"
fi

cd ../vEcoli || exit 1
uv run --env-file /Users/alexanderpatrie/Desktop/repos/ecoli/vEcoli/.env \
       --project /Users/alexanderpatrie/Desktop/repos/ecoli/vEcoli \
       runscripts/workflow.py --config "$config_path"
