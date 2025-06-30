#!/bin/bash

ROOT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && cd .. && pwd )"

#generatorCliImage=openapitools/openapi-generator-cli:v7.1.0

# make a clean ROOT_DIR without .. (hint, use dirname or something like that)
SPEC_DIR="${ROOT_DIR}/sms_api/api/spec"
LIB_DIR="${ROOT_DIR}"

# Generate simdata-api client
# TODO: improve Python typing for Mypy
# TODO: make attributes dictionaries - easier to work with
PACKAGE="sms_api.api.client"
openapi-generator-cli generate -i "${SPEC_DIR}/openapi_3_1_0_generated.yaml" -g python -o "${LIB_DIR}" --additional-properties=packageName=${PACKAGE},generateSourceCodeOnly=true

